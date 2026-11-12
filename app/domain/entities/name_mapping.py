from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.entities.enums import KeyType, LinkStatus, MatchMethod


class NameCandidate(BaseModel):
    rxcui: str
    name: str | None = None
    source: str | None = None
    score: float | None = None
    method: MatchMethod = MatchMethod.APPROXIMATE


class NameMapping(BaseModel):
    """Auditable name-to-ingredient resolution. Never auto-accept a fuzzy match."""

    key_type: KeyType
    raw: str
    normalized: str
    candidates: list[NameCandidate] = Field(default_factory=list)
    status: LinkStatus = LinkStatus.UNREVIEWED
    method: MatchMethod = MatchMethod.UNMATCHED
    ingredient_rxcuis: list[str] = Field(default_factory=list)   # filled only for EXACT or accepted matches
    updated_at: datetime | None = None
