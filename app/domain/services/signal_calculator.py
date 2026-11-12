"""Disproportionality statistics for a 2x2 table (pure functions, no I/O)."""
import math
from dataclasses import dataclass

from app.domain.value_objects.contingency_table import ContingencyTable

Z_95 = 1.96


@dataclass(frozen=True)
class SignalMetrics:
    prr: float
    ci_lower: float
    ci_upper: float
    chi_square: float


def compute_signal(t: ContingencyTable) -> SignalMetrics | None:
    """PRR = [a/(a+b)] / [c/(c+d)], 95% CI on ln(PRR), and the 2x2 chi-square (no continuity correction).

    Returns None when undefined (a == 0, c == 0 or an empty margin).
    """
    a, b, c, d = t.a, t.b, t.c, t.d
    if a == 0 or c == 0 or (a + b) == 0 or (c + d) == 0:
        return None
    prr = (a / (a + b)) / (c / (c + d))
    se = math.sqrt(1 / a - 1 / (a + b) + 1 / c - 1 / (c + d))
    ln_prr = math.log(prr)
    n = t.total
    denom = (a + b) * (c + d) * (a + c) * (b + d)
    chi_square = n * (a * d - b * c) ** 2 / denom if denom else 0.0
    return SignalMetrics(prr, math.exp(ln_prr - Z_95 * se), math.exp(ln_prr + Z_95 * se), chi_square)
