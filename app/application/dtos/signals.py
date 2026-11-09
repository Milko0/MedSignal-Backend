from typing import Literal

from pydantic import BaseModel

from app.application.dtos.common import Meta, Page


class SignalItem(BaseModel):
    rxcui: str
    drug: str
    reaction: str
    reports: int
    prr: float
    ci_lower: float
    chi_square: float
    in_label: bool | None = None
    novelty: Literal["known", "literature", "novel"] | None = None
    trend: list[float] = []


class SignalListResponse(BaseModel):
    meta: Meta = Meta()
    page: Page = Page()
    items: list[SignalItem]


class ReportItem(BaseModel):
    report_id: str
    receive_date: str
    serious: bool
    sex: str | None = None
    age_group: str | None = None
    country: str | None = None
    reactions: list[str] = []


class SignalReportsResponse(BaseModel):
    meta: Meta = Meta()
    page: Page = Page()
    items: list[ReportItem]


class StatisticsResponse(BaseModel):
    meta: Meta = Meta()
    by_age_group: dict[str, int] = {}
    by_sex: dict[str, int] = {}
    by_country: dict[str, int] = {}
    serious_over_time: list[dict] = []  # [{"quarter": "Q3 2026", "serious": 118, "all": 420}]
