import pytest

from app.domain.services.emerging_signal_policy import meets_evans_criteria
from app.domain.services.signal_calculator import compute_signal
from app.domain.value_objects.contingency_table import ContingencyTable


def test_ibuprofen_gi_haemorrhage_matches_validation_run():
    s = compute_signal(ContingencyTable(a=551, b=42319, c=9543, d=3609701))
    assert s.prr == pytest.approx(4.87, abs=0.01)
    assert s.ci_lower == pytest.approx(4.48, abs=0.02)
    assert s.chi_square == pytest.approx(1609, rel=0.01)
    assert meets_evans_criteria(s, report_count=551)


def test_no_signal_when_few_reports():
    s = compute_signal(ContingencyTable(a=2, b=1000, c=500, d=100000))
    assert not meets_evans_criteria(s, report_count=2)


def test_zero_cell_returns_none():
    assert compute_signal(ContingencyTable(a=0, b=10, c=5, d=100)) is None
