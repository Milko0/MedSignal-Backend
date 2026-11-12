import os
from datetime import UTC, datetime

import pytest

# Tests never read the developer's .env secrets; a 32+ char key silences PyJWT's weak-key warning.
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-characters-long")

from app.application.services.alert_dispatcher import AlertDispatcher
from app.application.services.ingredient_resolver import IngredientResolver
from app.application.use_cases.ingestion.build_clean_dataset import BuildCleanDataset
from app.infrastructure.clock import FixedClock
from app.infrastructure.memory.factory import build_memory_container
from tests.fixtures import raw
from tests.fixtures.fakes import FakeNormalizer


class ListFeed:
    """All feeds over in-memory lists of raw dictionaries."""

    def __init__(self, reports, products, labels, recalls, shortages):
        self.d = {"reports": reports, "products": products, "labels": labels, "recalls": recalls, "shortages": shortages}

    async def _it(self, key, limit=None):
        for r in self.d[key][:limit]:
            yield r

    def fetch_shortages(self): return self._it("shortages")
    def fetch_products(self, limit=None): return self._it("products", limit)
    def fetch_labels(self, limit=None): return self._it("labels", limit)
    def fetch_recalls(self, limit=None): return self._it("recalls", limit)
    def read_bulk_file(self, path): return self._it("reports")
    async def last_updated(self): return "2026-11-10"


@pytest.fixture
def clock():
    return FixedClock(datetime(2026, 11, 10, 12, 0, tzinfo=UTC))


@pytest.fixture
def feed():
    return ListFeed(raw.build_reports(), raw.ndc_products(), raw.labels(), raw.recalls(), raw.shortages())


@pytest.fixture
async def world(clock, feed):
    """A fully built container: the whole pipeline ran on the synthetic raw data."""
    c = build_memory_container(clock)
    from app.domain.entities.excluded_term import ExcludedTerm
    for t in ("DRUG INEFFECTIVE", "OFF LABEL USE"):
        await c.excluded_terms.add(ExcludedTerm(term=t, added_at=clock.now()))
    normalizer = FakeNormalizer()
    resolver = IngredientResolver(normalizer, c.rx_concepts, c.ingredients, c.name_map, clock)
    dispatcher = AlertDispatcher(c.follows, c.alerts, c.users, clock)
    report = await BuildCleanDataset(c, resolver, feed, feed, feed, feed, feed, normalizer, dispatcher).execute(
        ["faers.json"], link_recalls=True)
    c.build_report = report
    c.normalizer = normalizer
    return c
