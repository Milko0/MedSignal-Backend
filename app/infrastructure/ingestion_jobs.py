"""Ingestion triggered over HTTP by an administrator (FR-19, FR-20), run in the background of the API process.

The work itself is the same use cases the scripts and the worker run; this only wires their adapters (openFDA,
RxNav, bulk files) and keeps one job of each kind at a time. Every run writes its own log (ingestion_runs, FR-21);
a job that crashes writes one with the error, so the admin always sees what happened in GET /admin/ingestion/runs.
"""
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.application.container import Container
from app.application.services.alert_dispatcher import AlertDispatcher
from app.application.services.ingredient_resolver import IngredientResolver
from app.application.use_cases.ingestion.apply_retention_window import ApplyRetentionWindow
from app.application.use_cases.ingestion.compute_quarter_signals import ComputeQuarterSignals
from app.application.use_cases.ingestion.load_faers_bulk import LoadFaersBulk
from app.application.use_cases.ingestion.poll_shortages import PollShortages
from app.application.use_cases.ingestion.update_labels_recalls import UpdateLabelsAndRecalls
from app.core.config import Settings
from app.domain.entities.enums import RunType
from app.domain.entities.ingestion_run import IngestionRun
from app.domain.exceptions import ValidationRuleError
from app.domain.services.retention_window import quarters_to_drop
from app.domain.value_objects.quarter import Quarter
from app.infrastructure.external.file_feeds import FileFeeds
from app.infrastructure.external.http import HttpFetcher
from app.infrastructure.external.openfda_client import OpenFdaFeeds
from app.infrastructure.external.rxnorm_client import RxNavClient
from app.infrastructure.external.rxnorm_normalizer import RxNormNormalizer

log = logging.getLogger("medsignal.ingestion")

FAERS = "faers"
INCREMENTAL = "incremental"
LABELS = "labels"
_QUARTER_IN_NAME = re.compile(r"^(\d{4})q([1-4])-", re.IGNORECASE)


class IngestionJobs:
    def __init__(self, c: Container, settings: Settings) -> None:
        self.c, self.s = c, settings
        self.running: set[str] = set()

    # ------------------------------------------------------------------ wiring
    def _resolver(self) -> IngredientResolver:
        rx = HttpFetcher(self.s.rxnorm_requests_per_second, self.s.http_max_retries, self.s.http_timeout_seconds)
        normalizer = RxNormNormalizer(RxNavClient(self.s, rx), self.s.cache_dir)
        return IngredientResolver(normalizer, self.c.rx_concepts, self.c.ingredients, self.c.name_map, self.c.clock,
                                  concurrency=self.s.rxnorm_concurrency)

    def _dispatcher(self) -> AlertDispatcher:
        return AlertDispatcher(self.c.follows, self.c.alerts, self.c.users, self.c.clock)

    def faers_paths(self, names: list[str]) -> list[str]:
        """Only plain file names inside FAERS_DIR are accepted: the API never reads an arbitrary path."""
        base = Path(self.s.faers_dir).resolve()
        paths = []
        for name in names:
            if Path(name).name != name:
                raise ValidationRuleError(f"Give a file name, not a path: {name}")
            path = base / name
            if not path.is_file():
                raise ValidationRuleError(f"{name} is not in {self.s.faers_dir}")
            paths.append(str(path))
        return paths

    async def faers_files(self) -> list[dict]:
        """The bulk files in FAERS_DIR (what download_faers.py left there), newest quarter first."""
        base = Path(self.s.faers_dir)
        if not base.is_dir():
            return []
        loaded = set(await self.c.reports.quarters())
        files = []
        for f in base.iterdir():
            if not f.is_file() or f.name.endswith(".part"):
                continue
            m = _QUARTER_IN_NAME.match(f.name)
            quarter = f"{m.group(1)}Q{m.group(2)}" if m else None
            st = f.stat()
            files.append({"name": f.name, "quarter": quarter, "size_mb": round(st.st_size / 1e6, 1),
                          "modified_at": datetime.fromtimestamp(st.st_mtime, UTC).isoformat(),
                          "quarter_loaded": quarter in loaded})
        return sorted(files, key=lambda x: (x["quarter"] or "", x["name"]), reverse=True)

    async def loaded_quarters(self, adding: str | None = None) -> dict:
        """The quarters in the database and, for `adding`, which ones a load would drop from the rolling window."""
        present = await self.c.reports.quarters()
        keep = self.s.faers_window_quarters
        out = {"window_quarters": keep, "quarters": present, "adding": None, "would_drop": []}
        if adding:
            if not re.fullmatch(r"\d{4}Q[1-4]", adding.strip(), re.IGNORECASE):
                raise ValidationRuleError(f"Not a quarter: {adding} (use e.g. 2026Q4)")
            q = str(Quarter.parse(adding.strip()))
            out["adding"] = q
            out["would_drop"] = quarters_to_drop(sorted({*present, q}), keep)
        return out

    # ------------------------------------------------------------------ jobs
    def start(self, kind: str) -> bool:
        if kind in self.running:
            return False
        self.running.add(kind)
        return True

    async def _guard(self, kind: str, run_type: RunType, source: str, work) -> None:
        try:
            await work()
        except Exception as exc:
            log.exception("%s ingestion failed", kind)
            now = self.c.clock.now()
            await self.c.ingestion_runs.add(IngestionRun(
                run_id=str(uuid.uuid4()), type=run_type, source=source, started_at=now, ended_at=now,
                errors=[f"{type(exc).__name__}: {exc}"]))
        finally:
            self.running.discard(kind)

    def _feeds(self) -> OpenFdaFeeds:
        return OpenFdaFeeds(self.s, HttpFetcher(self.s.openfda_requests_per_second, self.s.http_max_retries,
                                                self.s.http_timeout_seconds))

    async def _labels_and_recalls(self, label_limit: int | None, since_days: int | None) -> None:
        c, feeds = self.c, self._feeds()
        since = c.clock.now().date() - timedelta(days=since_days or self.s.incremental_lookback_days)
        await UpdateLabelsAndRecalls(feeds, feeds, c.labels, c.recalls, self._resolver(), self._dispatcher(),
                                     c.ingestion_runs, c.clock, tracked=c.ingredients).execute(label_limit, since)

    async def incremental(self, label_limit: int | None, since_days: int | None = None) -> None:
        """FR-20: shortage list (diffed, history kept, alerts), then the labels and recalls changed in the last
        `since_days` days (default INCREMENTAL_LOOKBACK_DAYS)."""
        async def work():
            c, feeds = self.c, self._feeds()
            await PollShortages(feeds, c.shortages, c.products, self._resolver(), c.shortage_status,
                                self._dispatcher(), c.ingestion_runs, c.clock).execute()
            await self._labels_and_recalls(label_limit, since_days)
        await self._guard(INCREMENTAL, RunType.INCREMENTAL, "openfda:shortages+labels+enforcement", work)

    async def labels_and_recalls(self, since_days: int | None = None) -> None:
        """The worker's daily job: labels and recalls changed in the last days (shortages have their own job)."""
        async def work():
            await self._labels_and_recalls(None, since_days)
        await self._guard(LABELS, RunType.INCREMENTAL, "openfda:labels+enforcement", work)

    async def faers(self, paths: list[str], window_quarters: int | None) -> None:
        """FR-19: load FAERS bulk files, keep the rolling window, recompute the signals of every quarter."""
        async def work():
            c = self.c
            run = await LoadFaersBulk(FileFeeds(self.s.faers_dir), c.reports, self._resolver(), c.ingestion_runs,
                                      c.clock).execute(paths, log=False)
            kept = await ApplyRetentionWindow(c.reports, c.signals, c.ingestion_runs, c.clock).execute(
                window_quarters or self.s.faers_window_quarters)
            compute = ComputeQuarterSignals(c.reports, c.signals, c.labels, c.excluded_terms, c.clock)
            for quarter in await c.reports.quarters():          # oldest first: "emerging" compares with the past
                await compute.execute(quarter)
            # The FULL_LOAD entry is written last, so it marks the end of the whole job (the admin screen waits for it)
            run.stats = {**run.stats, "quarters_kept": kept.kept, "quarters_dropped": kept.dropped,
                         "signals_recomputed": True}
            run.ended_at = c.clock.now()
            await c.ingestion_runs.add(run)
        await self._guard(FAERS, RunType.FULL_LOAD, "faers:" + ",".join(Path(p).name for p in paths), work)
