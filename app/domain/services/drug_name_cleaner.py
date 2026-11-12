"""Cleans drug names of FAERS entries. Use activesubstancename first, medicinalproduct last."""
import re

# Terms that carry no drug identity. Extend after reviewing the unmatched report (stats of the builder).
JUNK_TERMS = {
    "UNSPECIFIED INGREDIENT", "UNSPECIFIED", "UNKNOWN", "UNK", "NOT SPECIFIED", "NONE", "N/A", "NA",
    "PRODUCT", "DRUG", "UNKNOWN DRUG", "OMEGA 3",
}


def clean_name(raw) -> str:
    """Upper case, FAERS caret apostrophe restored (ST MARY^S THISTLE), single spaces."""
    if raw is None:
        return ""
    return " ".join(str(raw).replace("^", "'").strip().upper().split())


def is_junk(name) -> bool:
    cleaned = clean_name(name)
    return cleaned == "" or cleaned in JUNK_TERMS or re.fullmatch(r"[\W\d_]+", cleaned) is not None


def split_active_substances(raw) -> list[str]:
    """activesubstancename joins several substances with a backslash (CALCIUM CARBONATE\\CHOLECALCIFEROL)."""
    if raw is None:
        return []
    parts = [clean_name(p) for p in str(raw).split("\\")]
    seen: list[str] = []
    for p in parts:
        if p and not is_junk(p) and p not in seen:
            seen.append(p)
    return seen
