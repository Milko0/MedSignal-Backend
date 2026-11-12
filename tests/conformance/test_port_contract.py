"""Contract of the repository and store ports. Every adapter (memory today, MongoDB and Redis next) must pass the
same assertions. To add an adapter: register a builder in ADAPTERS that returns a Container."""
from datetime import UTC, datetime, timedelta

import pytest

from app.application.ingestion.transformers import transform_report
from app.domain.entities.alert import Alert
from app.domain.entities.drug import Drug, DrugClass
from app.domain.entities.enums import (
    AlertType,
    KeyType,
    LinkStatus,
    MatchMethod,
    RoleFilter,
    ShortageStatus,
)
from app.domain.entities.name_mapping import NameMapping
from app.domain.entities.recall import Recall, RecallLink
from app.domain.entities.shortage import ShortageRecord, ShortageSummary
from app.domain.entities.signal import SafetySignal
from app.domain.entities.user import User
from app.domain.exceptions import AlreadyExistsError
from app.infrastructure.clock import FixedClock
from app.infrastructure.memory.factory import build_memory_container
from tests.fixtures import raw

NOW = datetime(2026, 11, 10, tzinfo=UTC)
ADAPTERS = {"memory": lambda clock: build_memory_container(clock)}
# ADAPTERS["databases"] = lambda clock: <your Mongo + Redis container builder>   (phase 5)


@pytest.fixture(params=sorted(ADAPTERS))
def c(request):
    return ADAPTERS[request.param](FixedClock(NOW))


async def test_ingredient_search_and_class(c):
    await c.ingredients.upsert_many([
        Drug(rxcui="5640", name="IBUPROFEN", brand_names=["ADVIL"], atc=[DrugClass(class_id="M01AE", name="x")]),
        Drug(rxcui="7258", name="NAPROXEN", atc=[DrugClass(class_id="M01AE", name="x")])])
    assert (await c.ingredients.search("ibuprofin"))[0][0].rxcui == "5640"      # typo
    assert (await c.ingredients.search("advil"))[0][0].rxcui == "5640"          # brand name
    assert (await c.ingredients.search("zzzzzz")) == []
    assert {d.rxcui for d in await c.ingredients.list_by_class("M01AE")} == {"5640", "7258"}
    assert await c.ingredients.count() == 2 and await c.ingredients.get("0") is None


async def test_report_upsert_keeps_highest_version_and_counts(c):
    r1 = transform_report(raw.faers(1, 1, [raw._drug("X", "1", "197805")], ["Nausea"], version="2"), {"197805": ["5640"]})
    old = transform_report(raw.faers(1, 1, [raw._drug("X", "1", "197805")], ["Rash"], version="1"), {"197805": ["5640"]})
    other = transform_report(raw.faers(2, 1, [raw._drug("Y", "1", None)], ["Nausea"]))
    await c.reports.upsert_many([r1, other])
    await c.reports.upsert_many([old])                                           # an older version arrives later
    assert (await c.reports.get("10000001")).reaction_pts == ["NAUSEA"] and await c.reports.count() == 2
    pc = await c.reports.pair_counts("2026Q1", RoleFilter.SUSPECT, set())
    assert pc.total == 2 and pc.per_drug == {"5640": 1} and pc.per_pair == {("5640", "NAUSEA"): 1}
    assert pc.per_reaction["NAUSEA"] == 2                                       # the universe includes unresolved reports
    pc2 = await c.reports.pair_counts("2026Q1", RoleFilter.SUSPECT, {"NAUSEA"})
    assert pc2.per_pair == {} and await c.reports.quarters() == ["2026Q1"]
    assert await c.reports.delete("10000001") and not await c.reports.delete("10000001")
    assert await c.reports.delete_quarter("2026Q1") == 1 and await c.reports.quarters() == []   # rolling window


async def test_signal_search_and_history(c):
    mk = lambda q, prr, sig=True: SafetySignal(signal_id=SafetySignal.make_id(q, "1", "R"), quarter=q, ingredient_rxcui="1", reaction_term="R", a=25, b=5, c=3, d=70, prr=prr, ci_lower=1, chi_square=9, is_signal=sig)
    await c.signals.upsert_many([mk("2026Q1", 2.0), mk("2026Q2", 3.0), mk("2026Q3", 4.0, False)])
    found, total = await c.signals.search("2026Q3", None, None, 1, True, False, 0, 10)
    assert total == 0                                                            # only_signals filters the third
    found, total = await c.signals.search("2026Q2", "1", "R", 20, True, False, 0, 10)
    assert total == 1 and found[0].prr == 3.0
    assert await c.signals.previous_prrs("1", "R", "2026Q3") == [2.0, 3.0] and await c.signals.trend("1", "R", 2) == [3.0, 4.0]
    assert await c.signals.latest_quarter() == "2026Q3" and await c.signals.signal_count("1", "2026Q1") == 1
    assert await c.signals.delete_quarter("2026Q1") == 1 and await c.signals.delete_quarter("2026Q1") == 0
    assert await c.signals.previous_prrs("1", "R", "2026Q3") == [3.0]


async def test_shortage_replace_and_events(c):
    rec = lambda p, s: ShortageRecord(package_ndc=p, status=s, ingredient_rxcuis=["1"])
    await c.shortages.replace_current([rec("a", ShortageStatus.CURRENT), rec("b", ShortageStatus.RESOLVED)])
    await c.shortages.replace_current([rec("a", ShortageStatus.CURRENT)])         # b left the list
    assert set(await c.shortages.current_by_package()) == {"a"}
    assert [r.package_ndc for r in await c.shortages.find_by_ingredient("1")] == ["a"]


async def test_recall_links_and_share(c):
    ok = Recall(recall_number="1", link=RecallLink(status=LinkStatus.ACCEPTED, ingredient_rxcuis=["1"]))
    cand = Recall(recall_number="2", link=RecallLink(status=LinkStatus.CANDIDATE, candidates=[{"rxcui": "1", "name": "x"}]))
    await c.recalls.upsert_many([ok, cand])
    assert [r.recall_number for r in await c.recalls.find_by_ingredient("1")] == ["1"]
    assert len(await c.recalls.find_by_ingredient("1", accepted_only=False)) == 2
    assert await c.recalls.linked_share() == 0.5


async def test_name_map_roundtrip(c):
    m = NameMapping(key_type=KeyType.ACTIVESUBSTANCE, raw="X", normalized="X", method=MatchMethod.EXACT, status=LinkStatus.ACCEPTED, ingredient_rxcuis=["1"])
    await c.name_map.upsert_many([m])
    assert (await c.name_map.get(KeyType.ACTIVESUBSTANCE, "X")).ingredient_rxcuis == ["1"]
    assert await c.name_map.get(KeyType.MEDICINALPRODUCT, "X") is None
    assert list(await c.name_map.get_many(KeyType.ACTIVESUBSTANCE, ["X", "Y"])) == ["X"]


async def test_users_unique_and_excluded_terms(c):
    u = User(user_id="1", username="Ana", email="ana@x.com", password_hash="h")
    await c.users.create(u)
    with pytest.raises(AlreadyExistsError):
        await c.users.create(User(user_id="2", username="ana", email="other@x.com", password_hash="h"))
    assert (await c.users.get_by_username_or_email("ANA@X.COM")).user_id == "1"
    assert await c.users.delete("1") and not await c.users.delete("1")


async def test_follow_store_both_directions(c):
    await c.follows.follow("u1", "d1")
    await c.follows.follow("u2", "d1")
    assert await c.follows.list_followed("u1") == {"d1"} and await c.follows.followers("d1") == {"u1", "u2"}
    await c.follows.unfollow("u1", "d1")
    assert not await c.follows.is_following("u1", "d1") and await c.follows.followers("d1") == {"u2"}


async def test_alert_store_idempotent_ttl_dismiss(c):
    a = Alert(alert_id="x", user_id="u", type=AlertType.SIGNAL, drug_rxcui="1", message="m", created_at=NOW)
    assert await c.alerts.add(a, 60) and not await c.alerts.add(a, 60)           # replay creates nothing
    assert len(await c.alerts.list("u")) == 1
    c.clock.set(NOW + timedelta(seconds=61))
    assert await c.alerts.list("u") == []                                         # expired
    assert await c.alerts.add(a.model_copy(update={"created_at": c.clock.now()}), 60)   # an expired id can be created again
    assert await c.alerts.dismiss("u", "x") and not await c.alerts.dismiss("u", "x")


async def test_shortage_status_and_counters(c):
    s = ShortageSummary(ingredient_rxcui="1", worst_status=ShortageStatus.CURRENT, packages_in_shortage=2, packages_total=3)
    await c.shortage_status.set(s, 60)
    assert (await c.shortage_status.get("1")).packages_in_shortage == 2
    await c.shortage_status.delete("1")
    assert await c.shortage_status.get("1") is None
    await c.counters.set_count("1", "R", "2026Q1", 5)
    await c.counters.set_count("1", "R", "2026Q1", 5)                             # a replay does not double count
    assert await c.counters.get_count("1", "R", "2026Q1") == 5 and await c.counters.get_count("1", "X", "2026Q1") is None


async def test_revoked_tokens_expire(c):
    assert not await c.revoked_tokens.is_revoked("j1")
    await c.revoked_tokens.revoke("j1", 60)
    await c.revoked_tokens.revoke("j1", 60)                                       # idempotent
    assert await c.revoked_tokens.is_revoked("j1") and not await c.revoked_tokens.is_revoked("j2")
    c.clock.set(NOW + timedelta(seconds=61))
    assert not await c.revoked_tokens.is_revoked("j1")                           # gone with the token's lifetime
