"""Domain entity: AdverseEventReport."""
from dataclasses import dataclass


@dataclass
class AdverseEventReport:
    report_id: str
    receive_date: str
    quarter: str
    drugs: list[dict]  # raw_name, rxcui, role (suspect/concomitant)
    reactions: list[str]
    patient: dict  # age_group, sex
    serious: bool = False
    country: str | None = None
