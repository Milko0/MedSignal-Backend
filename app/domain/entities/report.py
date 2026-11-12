from datetime import date

from pydantic import BaseModel, Field

from app.domain.entities.enums import (
    AgeGroup,
    DrugRole,
    MatchMethod,
    ReactionOutcome,
    ReporterQualification,
    ReportType,
    Sex,
)


class Seriousness(BaseModel):
    serious: bool | None = None
    death: bool | None = None
    hospitalization: bool | None = None
    life_threatening: bool | None = None
    disabling: bool | None = None
    congenital_anomaly: bool | None = None
    other: bool | None = None


class Patient(BaseModel):
    sex: Sex = Sex.UNKNOWN
    age_years: float | None = None
    age_group: AgeGroup = AgeGroup.UNKNOWN
    weight_kg: float | None = None


class Reaction(BaseModel):
    pt: str
    outcome: ReactionOutcome = ReactionOutcome.UNKNOWN


class ReportedDrug(BaseModel):
    """One drug entry of a report. The openFDA block is NOT stored: only the ids and the match method."""

    raw_name: str | None = None
    active_substances: list[str] = Field(default_factory=list)
    role: DrugRole = DrugRole.OTHER
    indication: str | None = None
    route_code: str | None = None
    product_rxcuis: list[str] = Field(default_factory=list)
    ingredient_rxcuis: list[str] = Field(default_factory=list)
    match_method: MatchMethod = MatchMethod.UNMATCHED


class AdverseReport(BaseModel):
    """Compact FAERS report. Only the highest version of a case is kept."""

    report_id: str
    version: int = 1
    receive_date: date
    quarter: str
    report_type: ReportType = ReportType.OTHER
    reporter_qualification: ReporterQualification = ReporterQualification.UNKNOWN
    seriousness: Seriousness = Field(default_factory=Seriousness)
    patient: Patient = Field(default_factory=Patient)
    country: str | None = None
    duplicate: bool = False
    reactions: list[Reaction] = Field(default_factory=list)
    reaction_pts: list[str] = Field(default_factory=list)          # denormalised for the signal pipeline
    drugs: list[ReportedDrug] = Field(default_factory=list)
    suspect_ingredient_ids: list[str] = Field(default_factory=list)  # denormalised
    all_ingredient_ids: list[str] = Field(default_factory=list)      # denormalised (suspect + other)
