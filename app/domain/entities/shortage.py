from datetime import date, datetime

from pydantic import BaseModel, Field

from app.domain.entities.enums import (
    Availability,
    EventKind,
    MatchType,
    ShortageStatus,
    SignalProfile,
)


class ShortageRecord(BaseModel):
    """Current state of one package NDC in the FDA shortage list."""

    package_ndc: str
    ndc11: str | None = None
    product_ndc: str | None = None
    ingredient_rxcuis: list[str] = Field(default_factory=list)
    generic_name: str | None = None
    dosage_form: str | None = None
    routes: list[str] = Field(default_factory=list)
    status: ShortageStatus
    availability: Availability = Availability.UNKNOWN
    availability_raw: str | None = None
    shortage_reason: str | None = None
    company: str | None = None
    therapeutic_categories: list[str] = Field(default_factory=list)
    presentation: str | None = None
    initial_posting_date: date | None = None
    update_date: date | None = None
    discontinued_date: date | None = None
    first_seen: datetime | None = None
    last_seen: datetime | None = None


class ShortageEvent(BaseModel):
    """What changed between two daily snapshots (our own history, FR-28)."""

    package_ndc: str
    at: datetime
    kind: EventKind
    from_status: ShortageStatus | None = None
    to_status: ShortageStatus | None = None
    ingredient_rxcuis: list[str] = Field(default_factory=list)


class ShortageSummary(BaseModel):
    """Per ingredient (optionally per dosage form): the value cached in the key-value store."""

    ingredient_rxcui: str
    worst_status: ShortageStatus | None = None
    packages_in_shortage: int = 0
    packages_total: int = 0
    dosage_forms: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None


class SubstituteSuggestion(BaseModel):
    """FR-10: a substitute for a drug in shortage (computed, never stored)."""

    match_type: MatchType
    ingredient_rxcui: str
    name: str
    dosage_form: str | None = None
    routes: list[str] = Field(default_factory=list)
    recall_count: int = 0
    signal_profile: SignalProfile = SignalProfile.LOW
    products_available: int = 0
    rank: int = 0
