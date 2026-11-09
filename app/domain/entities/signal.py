"""Domain entity: Signal."""
from dataclasses import dataclass


@dataclass
class Signal:
    quarter: str
    rxcui: str
    reaction: str
    reports: int
    prr: float
    ci_lower: float
    chi_square: float
    in_label: bool | None = None
    novelty: str | None = None  # known / literature / novel
