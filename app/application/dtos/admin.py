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


class FaersFileDto(BaseModel):
    """A FAERS bulk file waiting in the FAERS folder, ready for POST /admin/ingestion/faers."""

    name: str
    quarter: str | None = Field(description="Quarter read from the file name (e.g. 2026Q3); null if not recognised")
    size_mb: float
    modified_at: str
    quarter_loaded: bool = Field(description="True when reports of this quarter are already in the database")


class LoadedQuartersDto(BaseModel):
    """The rolling FAERS window as it is now, and what a load would change."""

    window_quarters: int = Field(description="Quarters kept after every load (FAERS_WINDOW_QUARTERS)")
    quarters: list[str] = Field(description="Quarters with reports in the database, oldest first")
    adding: str | None = Field(default=None, description="The quarter passed in ?adding=, normalised")
    would_drop: list[str] = Field(default_factory=list,
                                  description="Quarters a load of `adding` would remove from the database")


class FaersLoadRequest(BaseModel):
    files: list[str] = Field(min_length=1, description="FAERS bulk file names inside the FAERS folder (data/faers), "
                                                       "e.g. 2026q3-drug-event-0001-of-0031.json.zip")
    window_quarters: int | None = Field(default=None, ge=1, le=20,
                                        description="Quarters to keep after loading (default FAERS_WINDOW_QUARTERS)")

    model_config = {"json_schema_extra": {"examples": [{"files": ["2026q3-drug-event-0005-of-0031.json.zip"]}]}}
