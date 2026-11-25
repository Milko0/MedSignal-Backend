"""Which MongoDB handle each query uses: analytics reads go to the secondaries handle, ingestion/batch reads and
all writes stay on the primary handle (docs/adr/0003-read-preference-per-use-case.md). No database needed."""
from pymongo.read_preferences import SecondaryPreferred

from app.core.config import Settings
from app.domain.entities.enums import RoleFilter
from app.infrastructure.mongodb.client import analytics_database
from app.infrastructure.mongodb.repositories.report_repository import MongoReportRepository
from app.infrastructure.mongodb.repositories.signal_repository import MongoSignalRepository


class _Cursor:
    def __init__(self, docs):
        self._docs = docs

    def __aiter__(self):
        async def gen():
            for d in self._docs:
                yield d
        return gen()


class FakeCol:
    def __init__(self, label, calls):
        self.label, self.calls = label, calls

    def find(self, *a, **k):
        self.calls.append((self.label, "find"))
        return _Cursor([])

    async def find_one(self, *a, **k):
        self.calls.append((self.label, "find_one"))

    async def count_documents(self, *a, **k):
        self.calls.append((self.label, "count_documents"))
        return 0

    async def aggregate(self, *a, **k):
        self.calls.append((self.label, "aggregate"))
        return _Cursor([])

    async def distinct(self, *a, **k):
        self.calls.append((self.label, "distinct"))
        return []


class FakeDb:
    def __init__(self, label, calls):
        self.label, self.calls = label, calls

    def __getitem__(self, name):
        return FakeCol(self.label, self.calls)


def _repos():
    calls = []
    db, read_db = FakeDb("primary", calls), FakeDb("secondary", calls)
    return MongoReportRepository(db, read_db), MongoSignalRepository(db, read_db), calls


async def test_report_analytics_reads_use_the_secondary_handle():
    reports, _, calls = _repos()
    await reports.statistics("sex", None, None)
    await reports.top_reactions("1", 10, RoleFilter.SUSPECT, set())
    await reports.list_for_pair("1", "NAUSEA", 0, 10)
    await reports.monthly_trend("1", ["NAUSEA"], 6)
    assert {label for label, _ in calls} == {"secondary"}


async def test_report_ingestion_reads_stay_on_the_primary_handle():
    reports, _, calls = _repos()
    await reports.pair_counts("2026Q1", RoleFilter.SUSPECT, set())
    await reports.match_coverage("2026Q1")
    await reports.quarters()
    await reports.count()
    await reports.get("r1")
    assert {label for label, _ in calls} == {"primary"}


async def test_signal_explorer_and_trends_use_the_secondary_handle():
    _, signals, calls = _repos()
    await signals.search("2026Q1", None, None, 20, True, False, 0, 10)
    await signals.trend("1", "NAUSEA")
    await signals.signal_count("1", "2026Q1")
    await signals.latest_quarter()
    assert {label for label, _ in calls} == {"secondary"}


async def test_signal_computation_reads_the_previous_quarters_from_the_primary():
    _, signals, calls = _repos()
    await signals.previous_prrs("1", "NAUSEA", "2026Q1")
    assert {label for label, _ in calls} == {"primary"}


async def test_without_a_read_handle_everything_uses_the_primary():
    calls = []
    reports = MongoReportRepository(FakeDb("primary", calls))
    await reports.statistics("sex", None, None)
    assert {label for label, _ in calls} == {"primary"}


def test_analytics_database_sets_secondary_preferred_with_bounded_staleness():
    class Db:
        def with_options(self, **kw):
            self.kw = kw
            return self

    db = Db()
    analytics_database(db, Settings(mongo_max_staleness_seconds=120))
    pref = db.kw["read_preference"]
    assert isinstance(pref, SecondaryPreferred) and pref.max_staleness == 120


def test_analytics_database_is_the_primary_handle_when_switched_off():
    db = object()
    assert analytics_database(db, Settings(mongo_read_secondaries=False)) is db
