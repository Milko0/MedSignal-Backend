"""Domain entity: DrugLabel."""
from dataclasses import dataclass


@dataclass
class DrugLabel:
    set_id: str
    rxcui: str
    product_type: str  # Rx or OTC
    effective_time: str
    sections: dict  # adverse_reactions, warnings, boxed_warning, ...
