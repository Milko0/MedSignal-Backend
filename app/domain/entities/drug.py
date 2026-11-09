"""Domain entity: Drug."""
from dataclasses import dataclass


@dataclass
class Drug:
    rxcui: str
    name: str
    kind: str = 'generic'
    drug_class: str | None = None
    dosage_form: str | None = None
    route: str | None = None
