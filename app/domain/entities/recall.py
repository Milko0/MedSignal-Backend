from datetime import date

from pydantic import BaseModel, Field

from app.domain.entities.enums import LinkMethod, LinkStatus, RecallClass, RecallStatus


class LinkCandidate(BaseModel):
    rxcui: str
    name: str
    score: float | None = None


class RecallLink(BaseModel):
    """86% of recalls have no identifiers, so the link to a drug is explicit, auditable and may be wrong."""

    status: LinkStatus = LinkStatus.UNREVIEWED
    method: LinkMethod | None = None
    ingredient_rxcuis: list[str] = Field(default_factory=list)
    candidates: list[LinkCandidate] = Field(default_factory=list)


class Recall(BaseModel):
    recall_number: str
    event_id: str | None = None
    classification: RecallClass = RecallClass.NOT_CLASSIFIED
    status: RecallStatus = RecallStatus.UNKNOWN
    reason: str | None = None
    product_description: str | None = None
    recalling_firm: str | None = None
    initiation_date: date | None = None
    report_date: date | None = None
    termination_date: date | None = None
    link: RecallLink = Field(default_factory=RecallLink)
