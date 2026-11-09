from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.application.dtos.common import Meta


class DrugSearchItem(BaseModel):
    rxcui: str
    name: str
    kind: Literal["generic", "brand"] = "generic"
    drug_class: str | None = None
    dosage_form: str | None = None


class ShortageStatus(BaseModel):
    status: Literal["Current", "To Be Discontinued", "Resolved", "None"] = "None"
    since: date | None = None
    expected_return: str | None = None


class RecallCounts(BaseModel):
    class_i: int = 0
    class_ii: int = 0
    class_iii: int = 0


class LabelSummary(BaseModel):
    set_id: str | None = None
    effective_date: date | None = None
    has_boxed_warning: bool = False


class ReactionCount(BaseModel):
    term: str
    count: int


class TopSignal(BaseModel):
    reaction: str
    reports: int
    prr: float
    ci_lower: float
    in_label: bool | None = None
    novelty: Literal["known", "literature", "novel"] | None = None


class Drug360Response(BaseModel):
    meta: Meta = Meta()
    rxcui: str
    name: str
    description: str | None = None
    drug_class: str | None = None
    dosage_form: str | None = None
    shortage: ShortageStatus = ShortageStatus()
    recalls: RecallCounts = RecallCounts()
    label: LabelSummary = LabelSummary()
    top_reactions: list[ReactionCount] = []
    top_signals: list[TopSignal] = []
    is_followed: bool = False


class TrendSeries(BaseModel):
    reaction: str
    months: list[str]
    counts: list[int]


class ReactionTrendResponse(BaseModel):
    meta: Meta = Meta()
    series: list[TrendSeries]


class LabelGapItem(BaseModel):
    reaction: str
    reports: int
    match: Literal["full", "partial", "gap"]


class LabelGapResponse(BaseModel):
    meta: Meta = Meta()
    rxcui: str
    items: list[LabelGapItem]
