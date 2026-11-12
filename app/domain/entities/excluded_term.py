from datetime import datetime

from pydantic import BaseModel


class ExcludedTerm(BaseModel):
    """Non-specific reaction term excluded from signals and label gaps (FR-26)."""

    term: str
    added_at: datetime | None = None
