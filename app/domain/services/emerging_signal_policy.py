"""FR-06: a pair is emerging when its latest-quarter PRR is clearly above the baseline of earlier quarters."""


def is_emerging(latest_prr: float, baseline_prrs: list[float], margin: float = 0.5) -> bool:
    if not baseline_prrs:
        return False
    return latest_prr >= (sum(baseline_prrs) / len(baseline_prrs)) + margin
