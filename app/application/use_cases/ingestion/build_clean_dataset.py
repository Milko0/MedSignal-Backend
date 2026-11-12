"""Builds the whole clean dataset in a container from raw feeds (phase 3 of the plan).

Order matters: products and labels first (they feed the ingredient maps), then shortages, recalls,
reports, and last the signals. The same container can then be exported to data/clean/*.jsonl.
"""
import logging
from dataclasses import dataclass, field

from app.application.container import Container
from app.application.ingestion.transformers.ndc_product import transform_ndc_product
from app.application.ports.external_data_source import NdcFeed
from app.application.services.ingredient_resolver import IngredientResolver
from app.application.use_cases.ingestion.apply_retention_window import (
    ApplyRetentionWindow,
)
from app.application.use_cases.ingestion.attach_brand_names import AttachBrandNames
from app.application.use_cases.ingestion.compute_quarter_signals import (
    ComputeQuarterSignals,
)
from app.application.use_cases.ingestion.link_recalls import LinkRecalls
from app.application.use_cases.ingestion.load_faers_bulk import LoadFaersBulk
from app.application.use_cases.ingestion.poll_shortages import PollShortages
from app.application.use_cases.ingestion.update_labels_recalls import (
    UpdateLabelsAndRecalls,
)
from app.domain.entities.enums import RoleFilter
from app.domain.exceptions import TransformError

log = logging.getLogger("medsignal.build")


@dataclass
class BuildReport:
    products: int = 0
    labels_runs: dict = field(default_factory=dict)
    shortage_run: dict = field(default_factory=dict)
    faers_run: dict = field(default_factory=dict)
    recall_links: dict = field(default_factory=dict)
    signals: list[dict] = field(default_factory=list)
    retention: dict = field(default_factory=dict)
    brand_names: int = 0
    skipped_products: int = 0


class BuildCleanDataset:
    def __init__(self, c: Container, resolver: IngredientResolver, ndc_feed: NdcFeed, label_feed, recall_feed,
                 shortage_feed, report_feed, normalizer=None, dispatcher=None) -> None:
        self.c, self.resolver = c, resolver
        self.ndc_feed, self.label_feed, self.recall_feed = ndc_feed, label_feed, recall_feed
        self.shortage_feed, self.report_feed, self.normalizer, self.dispatcher = shortage_feed, report_feed, normalizer, dispatcher

    async def execute(self, faers_paths: list[str], link_recalls: bool = False, min_a: int = 3,
                      window_quarters: int | None = None) -> BuildReport:
        c, out = self.c, BuildReport()
        log.info("1/6 products (NDC) and their RxNav ingredients")
        # 1. NDC products (carry the product rxcuis and the NDC -> ingredient map used by shortages)
        raw_products = [r async for r in self.ndc_feed.fetch_products()]
        rx_map = await self.resolver.resolve_products({x for r in raw_products for x in ((r.get("openfda") or {}).get("rxcui") or [])})
        products = []
        for r in raw_products:
            try:
                products.append(transform_ndc_product(r, rx_map))
            except TransformError:
                out.skipped_products += 1
        await c.products.upsert_many(products)
        out.products = len(products)
        log.info("2/6 labels and recalls")
        # 2. labels + recalls
        run = await UpdateLabelsAndRecalls(self.label_feed, self.recall_feed, c.labels, c.recalls, self.resolver,
                                           self.dispatcher, c.ingestion_runs, c.clock).execute()
        out.labels_runs = run.stats | {"loaded": run.records_loaded, "skipped": run.records_skipped}
        log.info("3/6 shortages")
        # 3. shortages (first snapshot: no events)
        run = await PollShortages(self.shortage_feed, c.shortages, c.products, self.resolver, c.shortage_status,
                                  self.dispatcher, c.ingestion_runs, c.clock).execute()
        out.shortage_run = {"loaded": run.records_loaded, "skipped": run.records_skipped, **run.stats}
        log.info("4/6 FAERS reports (names without codes are resolved here: the longest step)")
        # 4. reports
        run = await LoadFaersBulk(self.report_feed, c.reports, self.resolver, c.ingestion_runs, c.clock).execute(faers_paths)
        out.faers_run = {"loaded": run.records_loaded, "skipped": run.records_skipped, **run.stats}
        # 4a. brand names from the NDC products (every ingredient exists by now: products, labels and reports)
        out.brand_names = await AttachBrandNames(c.ingredients).execute(products)
        # 4b. rolling window: keep the latest N calendar quarters (drops stragglers of old quarters too)
        if window_quarters:
            kept = await ApplyRetentionWindow(c.reports, c.signals, c.ingestion_runs, c.clock).execute(window_quarters)
            out.retention = kept.__dict__
        log.info("5/6 recall links")
        # 5. recall links (candidates only)
        if link_recalls and self.normalizer is not None:
            stats = await LinkRecalls(c.recalls, self.normalizer, c.clock).execute()
            out.recall_links = stats.__dict__
        log.info("6/6 signals per quarter")
        # 6. signals, oldest quarter first so that is_emerging can look back
        compute = ComputeQuarterSignals(c.reports, c.signals, c.labels, c.excluded_terms, c.clock)
        for quarter in sorted(await c.reports.quarters()):
            for role in (RoleFilter.SUSPECT,):
                s = await compute.execute(quarter, role, min_a)
                out.signals.append(s.__dict__)
        return out
