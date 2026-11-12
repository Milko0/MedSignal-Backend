"""FR-20, FR-28: poll the shortage feed, diff against the stored snapshot, keep our own history, raise alerts."""
import uuid

from app.application.ingestion.transformers.shortage import transform_shortage
from app.application.ports.clock import Clock
from app.application.ports.external_data_source import ShortageFeed
from app.application.ports.ingestion_run_repository import IngestionRunRepository
from app.application.ports.product_repository import ProductRepository
from app.application.ports.shortage_repository import ShortageRepository
from app.application.ports.shortage_status_store import ShortageStatusStore
from app.application.services.alert_dispatcher import AlertDispatcher
from app.application.services.ingredient_resolver import IngredientResolver
from app.domain.entities.enums import AlertType, EventKind, RunType
from app.domain.entities.ingestion_run import IngestionRun
from app.domain.exceptions import TransformError
from app.domain.services.shortage_diff import diff_shortages
from app.domain.services.shortage_summary import summarize


class PollShortages:
    def __init__(self, feed: ShortageFeed, shortages: ShortageRepository, products: ProductRepository,
                 resolver: IngredientResolver, shortage_status: ShortageStatusStore,
                 dispatcher: AlertDispatcher, runs: IngestionRunRepository, clock: Clock) -> None:
        self.feed, self.shortages, self.products, self.resolver = feed, shortages, products, resolver
        self.shortage_status, self.dispatcher, self.runs, self.clock = shortage_status, dispatcher, runs, clock

    async def execute(self) -> IngestionRun:
        now = self.clock.now()
        run = IngestionRun(run_id=str(uuid.uuid4()), type=RunType.SHORTAGE_POLL, source="openfda:/drug/shortages",
                           started_at=now, source_last_updated=await self.feed.last_updated())
        raw = [r async for r in self.feed.fetch_shortages()]
        rx = {x for r in raw for x in ((r.get("openfda") or {}).get("rxcui") or [])}
        rx_map = await self.resolver.resolve_products(rx)
        product_map = await self.products.product_ingredient_map()

        records = []
        for r in raw:
            try:
                records.append(transform_shortage(r, product_map, rx_map, now))
            except TransformError as exc:
                run.records_skipped += 1
                if len(run.errors) < 20:
                    run.errors.append(str(exc))
        previous = await self.shortages.current_by_package()
        new_records, events = diff_shortages(previous, records, now, initial=not previous)
        await self.shortages.replace_current(new_records)
        if events:
            await self.shortages.add_events(events)

        touched = {i for e in events for i in e.ingredient_rxcuis} | {i for r in new_records for i in r.ingredient_rxcuis}
        for ingredient in touched:
            summary = summarize(ingredient, await self.shortages.find_by_ingredient(ingredient), now)
            await self.shortage_status.set(summary, 3600)
        alerts = 0
        for e in events:
            if e.kind is EventKind.STATUS_CHANGE or e.kind is EventKind.APPEARED:
                for ingredient in e.ingredient_rxcuis:
                    alerts += await self.dispatcher.dispatch(
                        AlertType.SHORTAGE, ingredient, f"{e.package_ndc}:{e.at.date().isoformat()}:{e.kind.value}",
                        f"Shortage status changed to {e.to_status.value if e.to_status else 'unknown'}", "shortage")
        run.records_loaded = len(new_records)
        run.stats = {"events": len(events), "alerts": alerts, "initial": int(not previous)}
        run.ended_at = self.clock.now()
        await self.runs.add(run)
        return run
