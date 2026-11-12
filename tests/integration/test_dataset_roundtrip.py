from app.infrastructure.memory.dataset import export_dataset, load_dataset
from app.infrastructure.memory.factory import build_memory_container
from tests.fixtures.raw import IBU


async def test_export_then_load_gives_the_same_answers(world, tmp_path, clock):
    meta = export_dataset(world, str(tmp_path))
    assert meta["files"]["reports.jsonl"]["records"] == 401 and meta["total_bytes"] > 0
    again = build_memory_container(clock)
    counts = await load_dataset(again, str(tmp_path))
    assert counts["reports.jsonl"] == 401 and counts["signals.jsonl"] == len(world.signals.all_items())
    a = await world.signals.search("2026Q2", IBU, None, 1, True, False, 0, 5)
    b = await again.signals.search("2026Q2", IBU, None, 1, True, False, 0, 5)
    assert [s.model_dump() for s in a[0]] == [s.model_dump() for s in b[0]]
    assert await again.recalls.linked_share() == await world.recalls.linked_share()
    assert len(await again.shortages.current_by_package()) == 3
