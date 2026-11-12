"""FR-07: is a frequently reported reaction mentioned in the label? FULL / PARTIAL / NONE."""
import re

from app.domain.entities.enums import LabelMatch
from app.domain.entities.label import LabelGapCandidate
from app.domain.value_objects.reaction_term import normalize_reaction

_STOP = {"AND", "THE", "OF", "OR", "NOS", "WITH", "FOR", "NOT", "DUE", "TO", "IN", "ON", "A", "AN"}


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[A-Z0-9]+", normalize_reaction(text)) if t not in _STOP and len(t) > 2]


def match_level(term: str, label_text: str) -> LabelMatch:
    """FULL: the whole term appears as a phrase. PARTIAL: some or all significant words appear apart.
    NONE: no significant word appears. First version: word matching, no MedDRA hierarchy or synonyms."""
    text = normalize_reaction(label_text)
    t = normalize_reaction(term)
    if not text or not t:
        return LabelMatch.NONE
    if t in text:
        return LabelMatch.FULL
    words = set(re.findall(r"[A-Z0-9]+", text))
    toks = _tokens(term)
    if toks and any(tok in words for tok in toks):
        return LabelMatch.PARTIAL
    return LabelMatch.NONE


def find_label_gaps(
    reported: list[tuple[str, int]],
    warnings_text: str,
    indications_text: str = "",
    excluded_terms: set[str] | None = None,
    min_reports: int = 20,
) -> list[LabelGapCandidate]:
    """reported: (reaction PT, report count). Returns every reaction not fully covered by the label, most
    reported first. in_indications marks reactions that are the disease the drug treats (for example
    pain for an analgesic): they are weak candidates."""
    excluded = {normalize_reaction(t) for t in (excluded_terms or set())}
    out: list[LabelGapCandidate] = []
    for term, count in reported:
        norm = normalize_reaction(term)
        if count < min_reports or norm in excluded:
            continue
        level = match_level(norm, warnings_text)
        if level is LabelMatch.FULL:
            continue
        in_ind = match_level(norm, indications_text) is LabelMatch.FULL
        out.append(LabelGapCandidate(reaction_term=norm, report_count=count, match_level=level, in_indications=in_ind))
    return sorted(out, key=lambda g: g.report_count, reverse=True)
