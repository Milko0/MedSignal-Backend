from dataclasses import dataclass, field


@dataclass
class PairCounts:
    """Counts needed to build every 2x2 table of one quarter without re-reading reports.

    total:      reports in the quarter (after filters)
    per_drug:   ingredient rxcui -> reports mentioning it (per the role filter)
    per_reaction: reaction PT -> reports with it
    per_pair:   (ingredient rxcui, reaction PT) -> reports with both
    """

    total: int = 0
    per_drug: dict[str, int] = field(default_factory=dict)
    per_reaction: dict[str, int] = field(default_factory=dict)
    per_pair: dict[tuple[str, str], int] = field(default_factory=dict)
