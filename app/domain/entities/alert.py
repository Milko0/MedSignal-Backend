"""Domain entity: Alert."""
from dataclasses import dataclass


@dataclass
class Alert:
    id: str
    user_id: str
    type: str  # signal | label | shortage | recall
    rxcui: str
    title: str
    detail: str
    created_at: str
