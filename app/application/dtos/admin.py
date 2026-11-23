from pydantic import BaseModel, EmailStr, Field

from app.domain.entities.enums import Role


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


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(min_length=8)
    role: Role = Role.USER

    model_config = {"json_schema_extra": {"examples": [
        {"username": "luca", "email": "luca@example.com", "password": "password123", "role": "user"}]}}


class AdminUserUpdate(BaseModel):
    """Only the fields sent are changed. A new password is stored hashed."""

    username: str | None = Field(default=None, min_length=3, max_length=32)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    role: Role | None = None

    model_config = {"json_schema_extra": {"examples": [{"role": "admin"}]}}


class IngestionStarted(BaseModel):
    """202 answer of an ingestion trigger: the job runs in the background; its log appears in /admin/ingestion/runs."""

    job: str
    status: str = "started"
    detail: str


class FaersLoadRequest(BaseModel):
    files: list[str] = Field(min_length=1, description="FAERS bulk file names inside the FAERS folder (data/faers), "
                                                       "e.g. 2026q3-drug-event-0001-of-0031.json.zip")
    window_quarters: int | None = Field(default=None, ge=1, le=20,
                                        description="Quarters to keep after loading (default FAERS_WINDOW_QUARTERS)")

    model_config = {"json_schema_extra": {"examples": [{"files": ["2026q3-drug-event-0005-of-0031.json.zip"]}]}}
