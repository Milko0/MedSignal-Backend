from pydantic import BaseModel, Field


class SignalRow(BaseModel):
    rxcui: str
    drug: str
    reaction: str
    quarter: str
    reports: int
    a: int
    b: int
    c: int
    d: int
    prr: float
    ci_lower: float
    chi_square: float
    is_signal: bool
    is_emerging: bool
    label_match: str   # FULL | PARTIAL | NONE
    trend: list[float] = Field(default_factory=list)


class SignalList(BaseModel):
    items: list[SignalRow]
    total: int
    quarter: str | None = None
    match_coverage: float = 0.0


class ReportBrief(BaseModel):
    report_id: str
    receive_date: str
    serious: bool | None = None
    age_group: str
    sex: str
    country: str | None = None
    reactions: list[str]
    suspect_drugs: list[str]


class SignalReports(BaseModel):
    items: list[ReportBrief]
    total: int


class StatBucket(BaseModel):
    group: str
    value: int


class Statistics(BaseModel):
    group_by: str
    buckets: list[StatBucket]
