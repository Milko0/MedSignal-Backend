"""FR-19, FR-29: stream FAERS bulk files into clean reports. Chunked so memory stays flat."""
import uuid
from collections.abc import Iterable

from app.application.ingestion.resolution import NameResolution
from app.application.ingestion.transformers.report import transform_report
from app.application.ports.clock import Clock
from app.application.ports.external_data_source import ReportFeed
from app.application.ports.ingestion_run_repository import IngestionRunRepository
from app.application.ports.report_repository import ReportRepository
from app.application.services.ingredient_resolver import IngredientResolver
from app.domain.entities.enums import RunType
from app.domain.entities.ingestion_run import IngestionRun
from app.domain.exceptions import TransformError
from app.domain.services.drug_name_cleaner import (
    clean_name,
    is_junk,
    split_active_substances,
)


def product_rxcuis(raws: Iterable[dict]) -> set[str]:
    out: set[str] = set()
    for r in raws:
        for d in (r.get("patient") or {}).get("drug") or []:
            out.update(str(x) for x in ((d.get("openfda") or {}).get("rxcui") or []))
    return out


def unresolved_names(raws: Iterable[dict], rx_map: dict[str, list[str]]) -> set[str]:
    """Names of drugs whose product rxcuis gave no ingredient: activesubstancename first, medicinalproduct last."""
    names: set[str] = set()
    for r in raws:
        for d in (r.get("patient") or {}).get("drug") or []:
            rxs = [str(x) for x in ((d.get("openfda") or {}).get("rxcui") or [])]
            if any(rx_map.get(x) for x in rxs):
                continue
            subs = split_active_substances((d.get("activesubstance") or {}).get("activesubstancename"))
            if subs:
                names.update(subs)
            else:
                n = clean_name(d.get("medicinalproduct"))
                if n and not is_junk(n):
                    names.add(n)
    return names


class LoadFaersBulk:
    def __init__(self, feed: ReportFeed, reports: ReportRepository, resolver: IngredientResolver,
                 runs: IngestionRunRepository, clock: Clock, chunk_size: int = 2000) -> None:
        self.feed, self.reports, self.resolver, self.runs, self.clock = feed, reports, resolver, runs, clock
        self.chunk_size = chunk_size

    async def _flush(self, chunk: list[dict], run: IngestionRun) -> None:
        rx_map = await self.resolver.resolve_products(product_rxcuis(chunk))
        name_map: dict[str, NameResolution] = await self.resolver.resolve_names(unresolved_names(chunk, rx_map))
        clean = []
        for raw in chunk:
            try:
                clean.append(transform_report(raw, rx_map, name_map))
            except TransformError as exc:
                run.records_skipped += 1
                if len(run.errors) < 20:
                    run.errors.append(str(exc))
        if clean:
            await self.reports.upsert_many(clean)
            run.records_loaded += len(clean)

    async def execute(self, paths: list[str]) -> IngestionRun:
        run = IngestionRun(run_id=str(uuid.uuid4()), type=RunType.FULL_LOAD, source="faers:" + ",".join(paths),
                           started_at=self.clock.now())
        chunk: list[dict] = []
        for path in paths:
            async for raw in self.feed.read_bulk_file(path):
                chunk.append(raw)
                if len(chunk) >= self.chunk_size:
                    await self._flush(chunk, run)
                    chunk = []
        if chunk:
            await self._flush(chunk, run)
        run.stats = {**self.resolver.stats, "match_coverage": round(await self.reports.match_coverage(None), 4)}
        run.ended_at = self.clock.now()
        await self.runs.add(run)
        return run
