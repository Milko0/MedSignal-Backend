from pydantic import BaseModel, Field


class DrugSearchResult(BaseModel):
    rxcui: str
    name: str
    brand_names: list[str] = Field(default_factory=list)
    matched: str
    score: float


class ShortageInfo(BaseModel):
    status: str | None = None             # CURRENT | TO_BE_DISCONTINUED | RESOLVED | None (no record)
    packages_in_shortage: int = 0
    packages_total: int = 0
    dosage_forms: list[str] = Field(default_factory=list)   # all forms with a record, for the form filter
    since: str | None = None
    reasons: list[str] = Field(default_factory=list)


class RecallsInfo(BaseModel):
    class_i: int = 0
    class_ii: int = 0
    class_iii: int = 0
    not_classified: int = 0
    total: int = 0
    linked_share: float = 0.0   # share of ALL recalls that are linked to a drug: the counts are a lower bound


class LabelSummary(BaseModel):
    available: bool = False
    product_types: list[str] = Field(default_factory=list)
    effective_date: str | None = None
    has_boxed_warning: bool = False
    description: str | None = None


class ReactionCount(BaseModel):
    reaction: str
    reports: int


class TrendPoint(BaseModel):
    month: str  # YYYY-MM
    reaction: str
    reports: int


class AtcClass(BaseModel):
    class_id: str
    name: str


class Drug360Response(BaseModel):
    rxcui: str
    name: str
    brand_names: list[str] = Field(default_factory=list)
    atc_classes: list[AtcClass] = Field(default_factory=list)
    selected_dosage_form: str | None = None
    selected_route: str | None = None
    shortage: ShortageInfo
    recalls: RecallsInfo
    label: LabelSummary
    top_reactions: list[ReactionCount]
    is_followed: bool = False
    match_coverage: float = 0.0   # share of reports whose drugs were resolved to an ingredient


class LabelGapRow(BaseModel):
    reaction: str
    reports: int
    match_level: str      # PARTIAL or NONE
    in_indications: bool = False


class LabelGapsData(BaseModel):
    label_available: bool
    comparable: bool = True      # False when only OTC labels exist (they have no adverse reaction section)
    note: str | None = None
    gaps: list[LabelGapRow] = Field(default_factory=list)
