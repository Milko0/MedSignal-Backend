"""Keeps the dataset to a rolling window of the latest N quarters (bounded size on the Virtual Lab and in data/clean).

Run after every FAERS load: the new quarter comes in, the oldest goes out. Idempotent: a second run drops nothing.
Signals of a dropped quarter go with its reports (their 2x2 tables can no longer be recomputed or traced, FR-09).
"""
import uuid
from dataclasses import dataclass, field

from app.application.ports.clock import Clock
from app.application.ports.ingestion_run_repository import IngestionRunRepository
from app.application.ports.report_repository import ReportRepository
from app.application.ports.signal_repository import SignalRepository
from app.domain.entities.enums import RunType
from app.domain.entities.ingestion_run import IngestionRun
from app.domain.services.retention_window import quarters_to_drop


@dataclass
class RetentionResult:
    kept: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    reports_deleted: int = 0
    signals_deleted: int = 0


class ApplyRetentionWindow:
    def __init__(self, reports: ReportRepository, signals: SignalRepository, runs: IngestionRunRepository,
                 clock: Clock) -> None:
        self.reports, self.signals, self.runs, self.clock = reports, signals, runs, clock

    async def execute(self, keep_quarters: int) -> RetentionResult:
        present = await self.reports.quarters()
        out = RetentionResult(dropped=quarters_to_drop(present, keep_quarters))
        for q in out.dropped:
            out.reports_deleted += await self.reports.delete_quarter(q)
            out.signals_deleted += await self.signals.delete_quarter(q)
        out.kept = [q for q in present if q not in out.dropped]
        if out.dropped:
            now = self.clock.now()
            await self.runs.add(IngestionRun(
                run_id=str(uuid.uuid4()), type=RunType.INCREMENTAL, source=f"retention:keep={keep_quarters}",
                started_at=now, ended_at=now, records_loaded=0, records_skipped=0,
                stats={"kept": ",".join(out.kept), "dropped": ",".join(out.dropped),
                       "reports_deleted": out.reports_deleted, "signals_deleted": out.signals_deleted}))
        return out
