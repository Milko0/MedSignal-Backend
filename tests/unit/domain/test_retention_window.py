import pytest

from app.application.use_cases.ingestion.apply_retention_window import ApplyRetentionWindow
from app.domain.services.retention_window import quarters_to_drop, window
from app.domain.value_objects.quarter import Quarter


def test_window_crosses_year_boundary():
    assert [str(q) for q in window(Quarter(2026, 1), 3)] == ["2025Q3", "2025Q4", "2026Q1"]
    with pytest.raises(ValueError):
        window(Quarter(2026, 1), 0)


def test_sliding_like_a_queue_and_stragglers_dropped():
    assert quarters_to_drop(["2025Q4", "2026Q1", "2026Q2", "2026Q3"], 4) == []
    # a new quarter arrives: the oldest leaves (a b c d -> b c d e)
    assert quarters_to_drop(["2025Q4", "2026Q1", "2026Q2", "2026Q3", "2026Q4"], 4) == ["2025Q4"]
    # late reports dated in an old quarter are outside the CALENDAR window even if few
    assert quarters_to_drop(["2019Q2", "2026Q2", "2026Q3"], 4) == ["2019Q2"]
    assert quarters_to_drop([], 4) == []


async def test_apply_retention_drops_reports_and_signals_once(world):
    assert await world.reports.quarters() == ["2026Q1", "2026Q2"]
    uc = ApplyRetentionWindow(world.reports, world.signals, world.ingestion_runs, world.clock)
    res = await uc.execute(keep_quarters=1)
    assert res.dropped == ["2026Q1"] and res.kept == ["2026Q2"] and res.reports_deleted > 0
    assert await world.reports.quarters() == ["2026Q2"]
    assert (await world.signals.search("2026Q1", None, None, 1, False, False, 0, 10))[1] == 0
    assert (await uc.execute(keep_quarters=1)).dropped == []                        # idempotent
