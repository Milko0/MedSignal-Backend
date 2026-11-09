"""FR-10: rank substitution candidates by recalls, then signal profile. Candidates must share route and dosage form."""


def rank(candidates: list[dict]) -> list[dict]:
    order = {"low": 0, "moderate": 1, "high": 2}
    return sorted(candidates, key=lambda c: (c["recalls"], order.get(c["signal_profile"], 3)))
