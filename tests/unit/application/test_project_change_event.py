from datetime import UTC, datetime

from app.application.services.alert_dispatcher import AlertDispatcher
from app.application.use_cases.sync.project_change_event import ProjectChangeEvent
from app.domain.entities.enums import ShortageStatus
from app.domain.entities.shortage import ShortageRecord
from app.domain.entities.signal import SafetySignal
from app.domain.entities.user import AlertSettings, User
from app.infrastructure.clock import FixedClock
from app.infrastructure.memory.factory import build_memory_container
from app.infrastructure.mongodb.documents import to_doc
from app.infrastructure.sync.change_stream_projector import ChangeStreamProjector

NOW = datetime(2026, 11, 10, tzinfo=UTC)


def _signal(a=30, is_signal=True):
    return SafetySignal(signal_id=SafetySignal.make_id("2026Q3", "1", "NAUSEA"), quarter="2026Q3",
                        ingredient_rxcui="1", reaction_term="NAUSEA", a=a, b=5, c=3, d=70, prr=3.2, ci_lower=1.5,
                        chi_square=9, is_signal=is_signal)


async def _setup():
    c = build_memory_container(FixedClock(NOW))
    await c.users.create(User(user_id="u1", username="a", email="a@x.com", password_hash="h"))
    await c.users.create(User(user_id="u2", username="b", email="b@x.com", password_hash="h",
                              settings=AlertSettings(min_reports=50)))
    await c.follows.follow("u1", "1")
    await c.follows.follow("u2", "1")
    project = ProjectChangeEvent(c.shortages, c.shortage_status, c.counters,
                                 AlertDispatcher(c.follows, c.alerts, c.users, c.clock), c.clock)
    return c, project


async def test_signal_sets_counter_and_alerts_once():
    c, project = await _setup()
    assert await project.signal_changed(_signal()) == 1               # u2 wants >= 50 reports
    assert await project.signal_changed(_signal()) == 0               # replay: nothing new
    assert await c.counters.get_count("1", "NAUSEA", "2026Q3") == 30
    assert [a.ref_id for a in await c.alerts.list("u1")] == [_signal().signal_id] and await c.alerts.list("u2") == []
    assert await project.signal_changed(_signal(a=12, is_signal=False)) == 0
    assert await c.counters.get_count("1", "NAUSEA", "2026Q3") == 12  # overwritten, not incremented


async def test_projector_maps_change_events():
    c, project = await _setup()
    await c.shortages.replace_current([ShortageRecord(package_ndc="p", status=ShortageStatus.CURRENT,
                                                      ingredient_rxcuis=["1"])])
    projector = ChangeStreamProjector(db=None, project=project, checkpoints=None)
    await projector.handle({"ns": {"coll": "signals"}, "fullDocument": to_doc(_signal(), "signal_id")})
    await projector.handle({"ns": {"coll": "shortages"}, "fullDocument": {"_id": "p", "ingredient_rxcuis": ["1"]}})
    await projector.handle({"ns": {"coll": "signals"}, "operationType": "delete"})          # no document: ignored
    assert len(await c.alerts.list("u1")) == 1
    assert (await c.shortage_status.get("1")).packages_in_shortage == 1
