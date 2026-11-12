"""Rules that decide when a metric is a signal (Evans criteria) and when it is emerging (FR-06)."""
from app.domain.services.signal_calculator import SignalMetrics

MIN_PRR = 2.0
MIN_CHI_SQUARE = 4.0
MIN_REPORTS = 3


def meets_evans_criteria(metrics: SignalMetrics, report_count: int) -> bool:
    return metrics.prr >= MIN_PRR and metrics.chi_square >= MIN_CHI_SQUARE and report_count >= MIN_REPORTS


def is_emerging(latest_prr: float, previous_prrs: list[float], factor: float = 1.5) -> bool:
    """The latest PRR is clearly above the average of the previous quarters."""
    if not previous_prrs:
        return False
    return latest_prr >= (sum(previous_prrs) / len(previous_prrs)) * factor
