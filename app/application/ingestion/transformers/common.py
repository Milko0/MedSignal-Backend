"""Small helpers shared by the transformers. Pure functions, no I/O."""
from collections.abc import Iterable

_EMPTY = {"", "N/A", "NA", "NONE", "NULL", "UNKNOWN"}


def blank_to_none(value):
    """Empty strings and N/A become None. Other values are returned stripped."""
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        return None if s.upper() in _EMPTY else s
    return value


def as_list(value) -> list:
    """FAERS sometimes sends an object where other reports send an array (reportduplicate)."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def unique(values: Iterable) -> list:
    out: list = []
    for v in values:
        if v is not None and v not in out:
            out.append(v)
    return out


def str_list(value) -> list[str]:
    return unique(str(v).strip() for v in as_list(value) if v is not None and str(v).strip())


def to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value, default: int | None = None) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default
