"""One parser for the five date formats of the sources. Returns the value plus its precision."""
import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class Precision(StrEnum):
    DAY = "day"
    MONTH = "month"
    YEAR = "year"


@dataclass(frozen=True)
class ParsedDate:
    value: date
    precision: Precision


_FORMATS = [
    (r"\d{8}", "%Y%m%d", Precision.DAY),                       # FAERS, recalls, NDC: 20240101
    (r"\d{6}", "%Y%m", Precision.MONTH),                       # FAERS partial: 202212 (format 610)
    (r"\d{4}", "%Y", Precision.YEAR),                          # FAERS partial: 2023 (format 602)
    (r"\d{2}/\d{2}/\d{4}", "%m/%d/%Y", Precision.DAY),         # shortages: 07/14/2023
    (r"\d{2}-[A-Za-z]{3}-\d{2}", "%d-%b-%y", Precision.DAY),    # NDC packages: 01-MAY-26
    (r"\d{2}-[A-Za-z]{3}-\d{4}", "%d-%b-%Y", Precision.DAY),
    (r"[A-Za-z]{3} \d{2}, \d{4}", "%b %d, %Y", Precision.DAY),   # DailyMed: Nov 09, 2026
    (r"\d{4}-\d{2}-\d{2}.*", "%Y-%m-%d", Precision.DAY),       # ISO
    (r"\d{4}-\d{2}", "%Y-%m", Precision.MONTH),
]


def parse_date(value) -> ParsedDate | None:
    """Parse any of the known formats. Empty, N/A and invalid values return None."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.upper() in {"N/A", "NA", "NULL", "NONE"}:
        return None
    for pattern, fmt, precision in _FORMATS:
        if re.fullmatch(pattern, s):
            text = s[:10] if fmt == "%Y-%m-%d" else s
            try:
                return ParsedDate(datetime.strptime(text, fmt).date(), precision)
            except ValueError:
                return None
    return None


def parse_day(value) -> date | None:
    """Convenience: the parsed date regardless of precision."""
    parsed = parse_date(value)
    return parsed.value if parsed else None
