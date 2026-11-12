import math
from datetime import UTC, datetime

from app.domain.entities.enums import (
    EventKind,
    LabelMatch,
    MatchType,
    ShortageStatus,
    SignalProfile,
)
from app.domain.entities.shortage import ShortageRecord, SubstituteSuggestion
from app.domain.services.alternative_ranker import (
    profile_from_signal_count,
    rank_alternatives,
)
from app.domain.services.emerging_signal_policy import is_emerging, meets_evans_criteria
from app.domain.services.label_gap_matcher import find_label_gaps, match_level
from app.domain.services.shortage_diff import diff_shortages
from app.domain.services.shortage_summary import summarize
from app.domain.services.signal_calculator import compute_signal
from app.domain.value_objects.contingency_table import ContingencyTable

NOW = datetime(2026, 11, 10, tzinfo=UTC)


def test_prr_known_values():
    m = compute_signal(ContingencyTable(20, 80, 50, 850))   # (20/100) / (50/900) = 3.6
    assert math.isclose(m.prr, 3.6) and m.ci_lower < m.prr < m.ci_upper and m.chi_square > 4
    assert compute_signal(ContingencyTable(0, 10, 5, 100)) is None


def test_prr_hand_computed_chi_square():
    t = ContingencyTable(11, 29, 4, 157)
    m = compute_signal(t)
    n = t.total
    expected = n * (11 * 157 - 29 * 4) ** 2 / ((40) * (161) * (15) * (186))
    assert math.isclose(m.chi_square, expected) and math.isclose(m.prr, (11 / 40) / (4 / 161))


def test_evans_and_emerging():
    m = compute_signal(ContingencyTable(20, 80, 50, 850))
    assert meets_evans_criteria(m, 20) and not meets_evans_criteria(m, 2)
    assert is_emerging(3.0, [1.5, 2.0]) and not is_emerging(2.0, [1.9, 2.0]) and not is_emerging(9, [])


def test_label_match_levels():
    text = "Gastrointestinal bleeding, ulceration. Nausea and rash were reported."
    assert match_level("Nausea", text) is LabelMatch.FULL
    assert match_level("GASTROINTESTINAL HAEMORRHAGE", text) is LabelMatch.PARTIAL   # one significant word only
    assert match_level("Alopecia", text) is LabelMatch.NONE
    assert match_level("Rash", "") is LabelMatch.NONE


def test_find_label_gaps():
    gaps = find_label_gaps(
        reported=[("RASH", 50), ("ALOPECIA", 40), ("DRUG INEFFECTIVE", 90), ("PAIN", 30), ("NAUSEA", 5)],
        warnings_text="rash", indications_text="relief of pain", excluded_terms={"drug ineffective"}, min_reports=20)
    assert [(g.reaction_term, g.in_indications) for g in gaps] == [("ALOPECIA", False), ("PAIN", True)]


def _rec(pkg, status, ingredient="1"):
    return ShortageRecord(package_ndc=pkg, status=status, ingredient_rxcuis=[ingredient], first_seen=NOW, last_seen=NOW)


def test_shortage_diff():
    old = {"a": _rec("a", ShortageStatus.CURRENT), "b": _rec("b", ShortageStatus.CURRENT)}
    new = [_rec("a", ShortageStatus.RESOLVED), _rec("c", ShortageStatus.CURRENT)]
    records, events = diff_shortages(old, new, NOW)
    kinds = {(e.package_ndc, e.kind) for e in events}
    assert kinds == {("a", EventKind.STATUS_CHANGE), ("b", EventKind.DISAPPEARED), ("c", EventKind.APPEARED)}
    assert {r.package_ndc for r in records} == {"a", "c"}
    _, none = diff_shortages({}, new, NOW, initial=True)
    assert none == []  # first snapshot is not noise


def test_summary_and_ranker():
    s = summarize("1", [_rec("a", ShortageStatus.RESOLVED), _rec("b", ShortageStatus.CURRENT)])
    assert s.worst_status is ShortageStatus.CURRENT and s.packages_in_shortage == 1 and s.packages_total == 2
    mk = lambda name, mt, rec, avail, prof=SignalProfile.LOW: SubstituteSuggestion(
        match_type=mt, ingredient_rxcui=name, name=name, recall_count=rec, products_available=avail, signal_profile=prof)
    ranked = rank_alternatives([mk("c", MatchType.SAME_CLASS, 0, 3), mk("b", MatchType.SAME_INGREDIENT, 2, 1),
                                mk("a", MatchType.SAME_INGREDIENT, 0, 2), mk("x", MatchType.SAME_INGREDIENT, 0, 0)])
    assert [r.name for r in ranked] == ["a", "b", "c"] and [r.rank for r in ranked] == [1, 2, 3]
    assert profile_from_signal_count(0) is SignalProfile.LOW and profile_from_signal_count(9) is SignalProfile.HIGH
