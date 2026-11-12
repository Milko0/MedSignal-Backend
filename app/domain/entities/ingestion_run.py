from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.entities.enums import RunType


class IngestionRun(BaseModel):
    """Log of one ingestion run (FR-21). source_last_updated comes from the API meta block."""

    run_id: str
    type: RunType
    source: str
    source_last_updated: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    records_loaded: int = 0
    records_skipped: int = 0
    errors: list[str] = Field(default_factory=list)
    stats: dict[str, float | int | str] = Field(default_factory=dict)
