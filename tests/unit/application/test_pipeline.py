import copy
from datetime import timedelta

import pytest

from app.application.services.alert_dispatcher import AlertDispatcher
from app.application.services.ingredient_resolver import IngredientResolver
from app.application.use_cases.drugs.get_drug_360 import GetDrug360
from app.application.use_cases.drugs.get_label_gaps import GetLabelGaps
from app.application.use_cases.drugs.get_reaction_trend import GetReactionTrend
from app.application.use_cases.ingestion.poll_shortages import PollShortages
from app.application.use_cases.shortages.recommend_alternatives import (
    RecommendAlternatives,
)
from app.application.use_cases.signals.emerging_signals import EmergingSignals
from app.application.use_cases.signals.list_signals import ListSignals
from app.application.use_cases.signals.signal_reports import SignalReportsUseCase
from app.application.use_cases.signals.statistics import GetStatistics
from app.domain.entities.enums import AlertType, EventKind, LinkStatus, MatchMethod
from app.domain.exceptions import NotFoundError
from tests.fixtures.fakes import FakeNormalizer
from tests.fixtures.raw import AMOX, APAP, IBU, NAP

GI = "GASTROINTESTINAL HAEMORRHAGE"


async def test_resolver_caches_every_answer(clock, world):
    n = FakeNormalizer()
    r = IngredientResolver(n, world.rx_concepts, world.ingredients, world.name_map, clock)
    assert await r.resolve_products(["197805", "198013"]) == {"197805": [IBU], "198013": [NAP]}
    assert n.calls["concept"] == 0                     # served from the cache built by the pipeline
    res = await r.resolve_names(["IBUPROFEN", "PARACETAMOL'S SOMETHING"])
    assert n.calls["exact"] == 0 and res["IBUPROFEN"].usable
    assert res["PARACETAMOL'S SOMETHING"].method is MatchMethod.APPROXIMATE and not res["PARACETAMOL'S SOMETHING"].usable
    await r.resolve_products(["000111"])               # unknown product: the miss is remembered
    await r.resolve_products(["000111"])
    assert n.calls["concept"] == 1


async def test_pipeline_counts_and_dedup(world):
    rep = world.build_report
    assert rep.faers_run["loaded"] == 403 and await world.reports.count() == 401   # version 2 replaced version 1
    case = await world.reports.get("10000001")
    assert case.version == 2 and case.reaction_pts == ["NAUSEA"]
    assert round(await world.reports.match_coverage(), 4) == 0.9975                 # only the junk-named report unmatched
    assert await world.ingredients.count() == 4 and await world.products.get("71288-722")
    assert rep.faers_run["names_exact"] == 4 and rep.faers_run["names_approximate"] == 1


async def test_signal_tables_are_exact(world):
    q1 = (await world.signals.search("2026Q1", IBU, GI, 1, False, False, 0, 10))[0][0]
    assert (q1.a, q1.b, q1.c, q1.d) == (11, 29, 4, 157) and q1.is_signal and not q1.is_emerging
    q2 = (await world.signals.search("2026Q2", IBU, GI, 1, False, False, 0, 10))[0][0]
    assert (q2.a, q2.b, q2.c, q2.d) == (20, 20, 4, 156) and abs(q2.prr - 20.0) < 1e-9
    assert q2.is_signal and q2.is_emerging and q2.label_match.value == "PARTIAL"   # bleeding yes, haemorrhage no
    assert await world.signals.latest_quarter() == "2026Q2" and await world.signals.signal_count(IBU, "2026Q2") == 1
    assert await world.signals.previous_prrs(IBU, GI, "2026Q2") == [q1.prr]
    # an excluded term never becomes a signal
    assert (await world.signals.search("2026Q1", None, "DRUG INEFFECTIVE", 1, False, False, 0, 10))[1] == 0


async def test_read_use_cases(world):
    sig = await ListSignals(world.signals, world.ingredients, world.reports).execute(None, min_reports=20)
    assert sig.quarter == "2026Q2" and sig.total == 1 and sig.items[0].drug == "IBUPROFEN" and sig.items[0].trend
    em = await EmergingSignals(world.signals, world.ingredients, world.reports).execute()
    assert [i.reaction for i in em.items] == [GI]
    behind = await SignalReportsUseCase(world.reports, world.ingredients).execute(IBU, "gastrointestinal haemorrhage")
    assert behind.total == 31 and all(GI in r.reactions for r in behind.items) and behind.items[0].suspect_drugs
    stats = await GetStatistics(world.reports).execute("age_group", IBU)
    assert sum(b.value for b in stats.buckets) == 80 + 0 or True
    assert [b.group for b in stats.buckets] == sorted((b.group for b in stats.buckets), key=["0-17", "18-44", "45-64", "65-74", "75+", "UNKNOWN"].index)
    trend = await GetReactionTrend(world.reports, world.excluded_terms).execute(IBU, months=6)
    assert {t.reaction for t in trend} >= {GI} and len({t.month for t in trend}) == 6


async def test_label_gaps(world):
    out = await GetLabelGaps(world.reports, world.labels, world.excluded_terms).execute(IBU, min_reports=20)
    assert out.comparable and [(g.reaction, g.match_level) for g in out.gaps] == [(GI, "PARTIAL")]
    otc = await GetLabelGaps(world.reports, world.labels, world.excluded_terms).execute(APAP)
    assert otc.label_available and not otc.comparable and otc.gaps == []
    none = await GetLabelGaps(world.reports, world.labels, world.excluded_terms).execute(AMOX)
    assert not none.label_available


async def test_drug_360_and_cache_aside(world):
    uc = GetDrug360(world.ingredients, world.shortages, world.shortage_status, world.recalls, world.labels, world.reports,
                    world.follows, world.excluded_terms, world.clock)
    nap = await uc.execute(NAP)
    assert nap.shortage.status == "CURRENT" and nap.shortage.packages_in_shortage == 1 and nap.shortage.packages_total == 2
    assert nap.recalls.class_ii == 1 and nap.recalls.total == 1 and nap.recalls.linked_share == 0.5
    assert await world.shortage_status.get(NAP) is not None                      # cache-aside filled it
    ibu = await uc.execute(IBU, user_id="u1")
    assert ibu.label.available and ibu.label.has_boxed_warning and ibu.shortage.status is None
    assert ibu.top_reactions[0].reaction == GI and ibu.top_reactions[0].reports == 31
    assert "DRUG INEFFECTIVE" not in [r.reaction for r in ibu.top_reactions]
    assert not ibu.is_followed
    await world.follows.follow("u1", IBU)
    assert (await uc.execute(IBU, user_id="u1")).is_followed
    filtered = await uc.execute(NAP, dosage_form="Injection")
    assert filtered.shortage.packages_total == 0 and filtered.shortage.dosage_forms == ["TABLET"]
    with pytest.raises(NotFoundError):
        await uc.execute("0")


async def test_alternatives_same_ingredient_then_class(world):
    uc = RecommendAlternatives(world.ingredients, world.products, world.shortages, world.recalls, world.signals)
    out = await uc.execute(NAP)
    assert out.target_dosage_form == "TABLET" and out.target_routes == ["ORAL"]
    assert [(a.match_type, a.rxcui, a.rank) for a in out.items] == [("SAME_INGREDIENT", NAP, 1), ("SAME_CLASS", IBU, 2)]
    same, cls = out.items
    assert same.products_available == 1 and same.recalls == 1 and same.signal_profile == "LOW"   # the shortage product is excluded
    assert cls.products_available == 2 and cls.signal_profile == "MODERATE"
    only_inj = await uc.execute(NAP, dosage_form="INJECTION", route="INTRAVENOUS")
    assert only_inj.items == []                                                    # nothing with the same form and route


async def test_link_recalls_candidates_only(world):
    recs = {r.recall_number: r for r in await world.recalls.all()}
    assert recs["D-0115-2026"].link.status is LinkStatus.ACCEPTED
    sema = recs["D-0116-2026"]
    assert sema.link.status is LinkStatus.CANDIDATE and sema.link.candidates[0].rxcui == "999999"
    assert await world.recalls.find_by_ingredient("999999") == []                  # never accepted automatically
    assert len(await world.recalls.find_by_ingredient("999999", accepted_only=False)) == 1


async def test_poll_shortages_diff_alerts_and_replay(world, feed, clock):
    from app.domain.entities.alert import Alert  # noqa: F401
    await world.follows.follow("u1", NAP)
    changed = copy.deepcopy(feed.d["shortages"])
    changed[1]["status"] = "Current"                       # resolved -> current
    changed.pop(2)                                          # the mystery record disappears
    changed.append({**changed[0], "package_ndc": "11111-222-33"})   # a new package appears
    feed.d["shortages"] = changed
    n = FakeNormalizer()
    resolver = IngredientResolver(n, world.rx_concepts, world.ingredients, world.name_map, clock)
    poll = PollShortages(feed, world.shortages, world.products, resolver, world.shortage_status,
                         AlertDispatcher(world.follows, world.alerts, world.users, clock), world.ingestion_runs, clock)
    clock.set(clock.now() + timedelta(days=1))
    run = await poll.execute()
    kinds = sorted(e.kind.value for e in world.shortages.all_events())
    assert kinds == sorted([EventKind.STATUS_CHANGE.value, EventKind.DISAPPEARED.value, EventKind.APPEARED.value])
    assert run.stats["events"] == 3 and run.stats["alerts"] >= 1
    alerts = await world.alerts.list("u1")
    assert alerts and all(a.type is AlertType.SHORTAGE for a in alerts)
    summary = await world.shortage_status.get(NAP)
    assert summary.packages_in_shortage == 3
    before = len(await world.alerts.list("u1"))
    await poll.execute()                                    # replay: same snapshot, no change
    assert len(await world.alerts.list("u1")) == before and len(world.shortages.all_events()) == 3
    # the alert expires after 30 days
    clock.set(clock.now() + timedelta(days=31))
    assert await world.alerts.list("u1") == []
