"""Rolling window of FAERS quarters: the dataset keeps the latest N calendar quarters and drops the rest.

Like a fixed-size queue: with N = 4 and quarters [Q1 Q2 Q3 Q4], loading Q5 drops Q1 -> [Q2 Q3 Q4 Q5].
The window is anchored on the newest quarter present, and it is a CALENDAR window, so late-arriving
reports whose receive date falls in an old quarter (stragglers in a recent FDA file) are dropped too:
they would otherwise form tiny quarters whose 2x2 tables give meaningless PRRs.
"""
from app.domain.value_objects.quarter import Quarter


def window(latest: Quarter, keep: int) -> list[Quarter]:
    """The `keep` calendar quarters ending at `latest`, oldest first."""
    if keep < 1:
        raise ValueError("keep must be >= 1")
    out = [latest]
    while len(out) < keep:
        out.append(out[-1].previous())
    return out[::-1]


def quarters_to_drop(present: list[str], keep: int) -> list[str]:
    """Quarters (as 'YYYYQn') outside the window anchored on the newest one present, oldest first."""
    if not present:
        return []
    parsed = sorted(Quarter.parse(q) for q in present)
    oldest_kept = window(parsed[-1], keep)[0]
    return [str(q) for q in parsed if q < oldest_kept]
