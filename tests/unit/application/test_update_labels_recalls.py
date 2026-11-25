"""Daily labels/recalls update (FR-20): date window passed to the feeds, untracked drugs skipped, re-runs harmless."""
import copy
import json
from datetime import date

from app.application.services.alert_dispatcher import AlertDispatcher
from app.application.services.ingredient_resolver import IngredientResolver
from app.application.use_cases.ingestion.update_labels_recalls import UpdateLabelsAndRecalls
from app.infrastructure.external.file_feeds import FileFeeds
from app.infrastructure.external.openfda_client import _since
from tests.fixtures import raw
from tests.fixtures.fakes import FakeNormalizer

SINCE = date(2026, 11, 3)


class RecordingFeed:
    def __init__(self, labels, recalls):
        self.labels, self.recalls, self.since = labels, recalls, []

    async def _it(self, items):
        for r in items:
            yield r

    def fetch_labels(self, limit=None, since=None):
        self.since.append(("labels", since))
        return self._it(self.labels)

    def fetch_recalls(self, limit=None, since=None):
        self.since.append(("recalls", since))
        return self._it(self.recalls)


def _use_case(world, clock, feed):
    resolver = IngredientResolver(FakeNormalizer(), world.rx_concepts, world.ingredients, world.name_map, clock)
    return UpdateLabelsAndRecalls(feed, feed, world.labels, world.recalls, resolver,
                                  AlertDispatcher(world.follows, world.alerts, world.users, clock), world.ingestion_runs,
                                  clock, tracked=world.ingredients)


async def test_only_labels_of_known_ingredients_are_added(world, clock):
    known = copy.deepcopy(raw.labels()[0]) | {"set_id": "CCCCCCCC-0000-4000-8000-000000000003"}
    unknown = copy.deepcopy(raw.labels()[0]) | {"set_id": "DDDDDDDD-0000-4000-8000-000000000004",
                                                 "openfda": {"rxcui": ["999999"]}}
    feed = RecordingFeed([known, unknown], [])
    run = await _use_case(world, clock, feed).execute(since=SINCE)
    assert await world.labels.get("cccccccc-0000-4000-8000-000000000003") is not None
    assert await world.labels.get("dddddddd-0000-4000-8000-000000000004") is None
    assert run.stats["labels_untracked"] == 1 and run.stats["since"] == "2026-11-03"
    assert feed.since == [("labels", SINCE), ("recalls", SINCE)]


async def test_rereading_the_same_window_raises_no_new_alert(world, clock):
    feed = RecordingFeed(raw.labels(), raw.recalls())           # already stored by the pipeline
    first = await _use_case(world, clock, feed).execute(since=SINCE)
    again = await _use_case(world, clock, feed).execute(since=SINCE)
    for run in (first, again):
        assert run.stats["label_alerts"] == 0 and run.stats["recall_alerts"] == 0


def test_openfda_date_window():
    assert _since("effective_time", SINCE) == "effective_time:[20261103 TO 99991231]"
    assert _since("report_date", None) is None


async def test_file_feeds_apply_the_same_window(tmp_path):
    (tmp_path / "labels.jsonl").write_text("\n".join(json.dumps({"effective_time": d}) for d in
                                                     ("20261101", "20261103", "20261120")))
    feeds = FileFeeds(str(tmp_path))
    assert [r["effective_time"] async for r in feeds.fetch_labels(since=SINCE)] == ["20261103", "20261120"]
    assert len([r async for r in feeds.fetch_labels()]) == 3
