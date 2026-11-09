"""PRR, 95% CI lower bound and chi-square. Pure functions, no I/O (unit-testable).

Screening rule (Evans): PRR >= 2, chi-square >= 4 and at least 3 reports.
Validation case from the data tests: a=551 b=42319 c=9543 d=3609701
-> PRR 4.87, CI lower 4.48, chi-square ~1609.
"""
import math
from dataclasses import dataclass

from app.domain.value_objects.contingency_table import ContingencyTable


@dataclass(frozen=True)
class SignalScore:
    prr: float
    ci_lower: float
    chi_square: float
    is_signal: bool


def compute_signal(t: ContingencyTable, min_reports: int = 3) -> SignalScore | None:
    if t.a == 0 or t.c == 0:
        return None
    prr = (t.a / (t.a + t.b)) / (t.c / (t.c + t.d))
    se = math.sqrt(1 / t.a - 1 / (t.a + t.b) + 1 / t.c - 1 / (t.c + t.d))
    ci_lower = math.exp(math.log(prr) - 1.96 * se)
    chi = t.n * (t.a * t.d - t.b * t.c) ** 2 / ((t.a + t.b) * (t.c + t.d) * (t.a + t.c) * (t.b + t.d))
    return SignalScore(prr, ci_lower, chi, prr >= 2 and chi >= 4 and t.a >= min_reports)
