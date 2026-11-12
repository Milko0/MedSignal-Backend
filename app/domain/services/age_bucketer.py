"""Derives the UI age bucket from onset age and unit. patientagegroup is sparse (22%), so it is only a fallback."""
from app.domain.entities.enums import AgeGroup
from app.domain.services.code_dictionary import AGE_UNIT_YEARS

# patientagegroup: 1 neonate, 2 infant, 3 child, 4 adolescent (all under 18); 5 adult and 6 elderly are too wide.
_MINOR_GROUPS = {"1", "2", "3", "4"}


def to_years(age, unit) -> float | None:
    try:
        value = float(age)
    except (TypeError, ValueError):
        return None
    factor = AGE_UNIT_YEARS.get(str(unit).strip() if unit is not None else "", None)
    if factor is None or value < 0:
        return None
    years = value * factor
    return years if years <= 120 else None  # implausible ages are data errors


def bucket(age_years: float | None, age_group_code=None) -> AgeGroup:
    if age_years is None:
        return AgeGroup.A0_17 if str(age_group_code).strip() in _MINOR_GROUPS else AgeGroup.UNKNOWN
    if age_years < 18:
        return AgeGroup.A0_17
    if age_years < 45:
        return AgeGroup.A18_44
    if age_years < 65:
        return AgeGroup.A45_64
    if age_years < 75:
        return AgeGroup.A65_74
    return AgeGroup.A75_PLUS
