from datetime import datetime

from pydantic import BaseModel

from app.domain.entities.enums import LabelMatch, RoleFilter


class SafetySignal(BaseModel):
    """Disproportionality result for one (quarter, ingredient, reaction) with the 2x2 counts kept."""

    signal_id: str  # "quarter|ingredient|reaction"
    quarter: str
    ingredient_rxcui: str
    reaction_term: str
    a: int
    b: int
    c: int
    d: int
    prr: float
    ci_lower: float
    chi_square: float
    is_signal: bool = False
    is_emerging: bool = False
    label_match: LabelMatch = LabelMatch.NONE
    role_filter: RoleFilter = RoleFilter.SUSPECT
    computed_at: datetime | None = None

    @property
    def report_count(self) -> int:
        return self.a

    @staticmethod
    def make_id(quarter: str, ingredient_rxcui: str, reaction_term: str, role_filter: str = "SUSPECT") -> str:
        return f"{quarter}|{ingredient_rxcui}|{reaction_term}|{role_filter}"
