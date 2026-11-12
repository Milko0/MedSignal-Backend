from datetime import date, datetime

from pydantic import BaseModel, Field

from app.domain.entities.enums import LabelMatch, ProductType


class LabelHistoryEntry(BaseModel):
    version: int
    effective_date: date | None = None
    detected_at: datetime | None = None


class DrugLabel(BaseModel):
    """One SPL label set. Sections are plain text (HTML tables dropped, arrays joined)."""

    set_id: str
    spl_id: str | None = None
    product_type: ProductType = ProductType.OTHER
    version: int = 1
    effective_date: date | None = None
    has_boxed_warning: bool = False
    product_ndcs: list[str] = Field(default_factory=list)
    ingredient_rxcuis: list[str] = Field(default_factory=list)
    sections: dict[str, str] = Field(default_factory=dict)
    history: list[LabelHistoryEntry] = Field(default_factory=list)


class LabelGapCandidate(BaseModel):
    """A frequently reported reaction that the label does not mention (computed, never stored)."""

    reaction_term: str
    report_count: int
    match_level: LabelMatch
    in_indications: bool = False
