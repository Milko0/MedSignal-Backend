from datetime import UTC, datetime

from app.application.services.shortage_status_reader import ShortageStatusReader
from app.application.use_cases.signals.list_signals import to_rows
from app.domain.entities.drug import Drug
from app.domain.entities.enums import ShortageStatus
from app.domain.entities.shortage import ShortageRecord
from app.domain.entities.signal import SafetySignal
from app.infrastructure.clock import FixedClock
from app.infrastructure.memory.factory import build_memory_container

NOW = datetime(2026, 11, 10, tzinfo=UTC)


def _signal(rxcui):
    return SafetySignal(signal_id=SafetySignal.make_id("2026Q3", rxcui, "R"), quarter="2026Q3", ingredient_rxcui=rxcui,
                        reaction_term="R", a=5, b=5, c=3, d=70, prr=3, ci_lower=1.2, chi_square=9, is_signal=True)


async def test_signal_rows_carry_the_shortage_status_and_fill_the_cache():
    c = build_memory_container(FixedClock(NOW))
    await c.ingredients.upsert_many([Drug(rxcui="1", name="A"), Drug(rxcui="2", name="B"), Drug(rxcui="3", name="C")])
    await c.shortages.replace_current([
        ShortageRecord(package_ndc="p1", status=ShortageStatus.CURRENT, ingredient_rxcuis=["1"]),
        ShortageRecord(package_ndc="p2", status=ShortageStatus.TO_BE_DISCONTINUED, ingredient_rxcuis=["2"])])
    reader = ShortageStatusReader(c.shortage_status, c.shortages, c.clock)
    rows = await to_rows([_signal("1"), _signal("2"), _signal("3")], c.ingredients, c.signals, reader)
    assert [(r.shortage_status, r.in_shortage) for r in rows] == [
        ("CURRENT", True), ("TO_BE_DISCONTINUED", False), (None, False)]
    assert (await c.shortage_status.get("1")).worst_status is ShortageStatus.CURRENT     # cache-aside filled it
