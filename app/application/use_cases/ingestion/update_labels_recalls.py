"""FR-20: incremental update of labels and recalls, with alerts for label changes and new recalls."""
import uuid

from app.application.ingestion.transformers.label import transform_label
from app.application.ingestion.transformers.recall import transform_recall
from app.application.ports.clock import Clock
from app.application.ports.external_data_source import LabelFeed, RecallFeed
from app.application.ports.ingestion_run_repository import IngestionRunRepository
from app.application.ports.label_repository import LabelRepository
from app.application.ports.recall_repository import RecallRepository
from app.application.services.alert_dispatcher import AlertDispatcher
from app.application.services.ingredient_resolver import IngredientResolver
from app.domain.entities.enums import AlertType, RunType
from app.domain.entities.ingestion_run import IngestionRun
from app.domain.entities.label import LabelHistoryEntry
from app.domain.exceptions import TransformError


class UpdateLabelsAndRecalls:
    def __init__(self, label_feed: LabelFeed, recall_feed: RecallFeed, labels: LabelRepository,
                 recalls: RecallRepository, resolver: IngredientResolver, dispatcher: AlertDispatcher,
                 runs: IngestionRunRepository, clock: Clock) -> None:
        self.label_feed, self.recall_feed, self.labels, self.recalls = label_feed, recall_feed, labels, recalls
        self.resolver, self.dispatcher, self.runs, self.clock = resolver, dispatcher, runs, clock

    async def execute(self, limit: int | None = None) -> IngestionRun:
        now = self.clock.now()
        run = IngestionRun(run_id=str(uuid.uuid4()), type=RunType.INCREMENTAL, source="openfda:labels+enforcement", started_at=now)
        label_alerts = recall_alerts = changed = 0

        raw_labels = [r async for r in self.label_feed.fetch_labels(limit)]
        rx_map = await self.resolver.resolve_products({x for r in raw_labels for x in ((r.get("openfda") or {}).get("rxcui") or [])})
        for r in raw_labels:
            try:
                new = transform_label(r, rx_map, now)
            except TransformError as exc:
                run.records_skipped += 1
                run.errors.append(str(exc))
                continue
            old = await self.labels.get(new.set_id)
            if old is not None and (new.version, new.effective_date) != (old.version, old.effective_date):
                changed += 1
                new = new.model_copy(update={"history": [*old.history, LabelHistoryEntry(
                    version=new.version, effective_date=new.effective_date, detected_at=now)]})
                for ing in new.ingredient_rxcuis:
                    label_alerts += await self.dispatcher.dispatch(
                        AlertType.LABEL, ing, f"{new.set_id}:v{new.version}", f"Label updated (version {new.version})", "label")
            elif old is not None:
                new = new.model_copy(update={"history": old.history})
            await self.labels.upsert_many([new])
            run.records_loaded += 1

        raw_recalls = [r async for r in self.recall_feed.fetch_recalls(limit)]
        rx_map = await self.resolver.resolve_products({x for r in raw_recalls for x in ((r.get("openfda") or {}).get("rxcui") or [])})
        known = {r.recall_number for r in await self.recalls.all()}
        fresh = []
        for r in raw_recalls:
            try:
                rec = transform_recall(r, rx_map)
            except TransformError as exc:
                run.records_skipped += 1
                run.errors.append(str(exc))
                continue
            fresh.append(rec)
            if rec.recall_number not in known:
                for ing in rec.link.ingredient_rxcuis:
                    recall_alerts += await self.dispatcher.dispatch(
                        AlertType.RECALL, ing, rec.recall_number, f"New {rec.classification.value} recall", "recall")
        await self.recalls.upsert_many(fresh)
        run.records_loaded += len(fresh)
        run.stats = {"labels_changed": changed, "label_alerts": label_alerts, "recall_alerts": recall_alerts}
        run.ended_at = self.clock.now()
        await self.runs.add(run)
        return run
