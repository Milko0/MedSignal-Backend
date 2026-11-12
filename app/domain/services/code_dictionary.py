"""Coded fields of the FAERS reports -> enums.

Verified (10 Nov 2026) against the openFDA field documentation as reproduced in published schema
descriptions: serious 1/2, patientsex 0/1/2, drugcharacterization 1/2/3, reactionoutcome 1-6,
reporttype 1-4, primarysource.qualification 1-5, patientagegroup 1-6, patientonsetageunit 800-805.
drugcharacterization 4 is not in the openFDA text; the E2B role list defines it as "drug not
administered", so it maps to OTHER and is never counted as suspect.
"""
from app.domain.entities.enums import (
    DrugRole,
    ReactionOutcome,
    ReporterQualification,
    ReportType,
    Sex,
)

_SEX = {"1": Sex.MALE, "2": Sex.FEMALE, "0": Sex.UNKNOWN}
_ROLE = {"1": DrugRole.SUSPECT, "2": DrugRole.CONCOMITANT, "3": DrugRole.INTERACTING, "4": DrugRole.OTHER}
_OUTCOME = {"1": ReactionOutcome.RECOVERED, "2": ReactionOutcome.RECOVERING, "3": ReactionOutcome.NOT_RECOVERED,
            "4": ReactionOutcome.RECOVERED_WITH_SEQUELAE, "5": ReactionOutcome.FATAL, "6": ReactionOutcome.UNKNOWN}
_REPORT_TYPE = {"1": ReportType.SPONTANEOUS, "2": ReportType.STUDY, "3": ReportType.OTHER, "4": ReportType.OTHER}
_QUALIFICATION = {"1": ReporterQualification.PHYSICIAN, "2": ReporterQualification.PHARMACIST,
                  "3": ReporterQualification.OTHER_HEALTH_PROFESSIONAL, "4": ReporterQualification.LAWYER,
                  "5": ReporterQualification.CONSUMER}
# patientonsetageunit -> years per unit (800 decade, 801 year, 802 month, 803 week, 804 day, 805 hour)
AGE_UNIT_YEARS = {"800": 10.0, "801": 1.0, "802": 1 / 12, "803": 7 / 365.25, "804": 1 / 365.25, "805": 1 / 8766}


def _key(code) -> str:
    return "" if code is None else str(code).strip()


def flag(code) -> bool | None:
    """1 = true, 2 = false, anything else = unknown."""
    return {"1": True, "2": False}.get(_key(code))


def sex(code) -> Sex:
    return _SEX.get(_key(code), Sex.UNKNOWN)


def drug_role(code) -> DrugRole:
    return _ROLE.get(_key(code), DrugRole.OTHER)


def reaction_outcome(code) -> ReactionOutcome:
    return _OUTCOME.get(_key(code), ReactionOutcome.UNKNOWN)


def report_type(code) -> ReportType:
    return _REPORT_TYPE.get(_key(code), ReportType.OTHER)


def reporter_qualification(code) -> ReporterQualification:
    return _QUALIFICATION.get(_key(code), ReporterQualification.UNKNOWN)
