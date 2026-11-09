from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class FaersLoadRequest(BaseModel):
    quarters: list[str]  # e.g. ["2026q2", "2026q3"]
    sample_ratio: float = 1.0  # < 1.0 to fit the Virtual Lab


class IngestionRunOut(BaseModel):
    id: str
    kind: Literal["faers_full", "incremental", "shortage_poll", "reconcile"]
    started_at: datetime
    finished_at: datetime | None = None
    records_loaded: int = 0
    errors: list[str] = []
    status: Literal["running", "ok", "failed"] = "running"


class ExcludedTerm(BaseModel):
    term: str


class ReconcileResult(BaseModel):
    counters_fixed: int = 0
    statuses_fixed: int = 0
    seconds: float = 0.0
