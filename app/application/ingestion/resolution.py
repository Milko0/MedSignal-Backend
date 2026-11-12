from dataclasses import dataclass, field

from app.domain.entities.enums import MatchMethod


@dataclass(frozen=True)
class NameResolution:
    """Result of resolving one drug name to ingredients. Only usable resolutions feed signals."""

    method: MatchMethod
    ingredient_rxcuis: list[str] = field(default_factory=list)
    usable: bool = False  # True for EXACT and for APPROXIMATE matches a person accepted
