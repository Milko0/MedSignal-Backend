from pydantic import BaseModel, Field


class IngestionRunDto(BaseModel):
    run_id: str
    type: str
    source: str
    source_last_updated: str | None = None
    started_at: str
    ended_at: str | None = None
    records_loaded: int = 0
    records_skipped: int = 0
    errors: list[str] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)


class ExcludedTermDto(BaseModel):
    term: str
