"""Domain entity: ShortageRecord."""
from dataclasses import dataclass


@dataclass
class ShortageRecord:
    rxcui: str
    status: str  # Current, To Be Discontinued, Resolved
    status_date: str
    package_ndc: str | None = None
    dosage_form: str | None = None
