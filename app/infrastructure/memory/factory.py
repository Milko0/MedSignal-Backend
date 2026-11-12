from app.application.container import Container
from app.domain.entities.excluded_term import ExcludedTerm
from app.infrastructure.clock import SystemClock
from app.infrastructure.memory import repositories as r
from app.infrastructure.memory import stores as s
from app.infrastructure.memory.dataset import load_dataset

# Non-specific reaction terms (FR-26). Editable by an admin; extend after reviewing the top reactions.
DEFAULT_EXCLUDED_TERMS = ["DRUG INEFFECTIVE", "OFF LABEL USE"]  # the two examples of FR-26


def build_memory_container(clock=None) -> Container:
    clock = clock or SystemClock()
    return Container(
        ingredients=r.MemoryIngredientRepository(), rx_concepts=r.MemoryRxConceptRepository(),
        products=r.MemoryProductRepository(), labels=r.MemoryLabelRepository(), shortages=r.MemoryShortageRepository(),
        recalls=r.MemoryRecallRepository(), name_map=r.MemoryNameMapRepository(), reports=r.MemoryReportRepository(),
        signals=r.MemorySignalRepository(), users=r.MemoryUserRepository(),
        excluded_terms=r.MemoryExcludedTermRepository(), ingestion_runs=r.MemoryIngestionRunRepository(),
        shortage_status=s.MemoryShortageStatusStore(), follows=s.MemoryFollowStore(),
        alerts=s.MemoryAlertStore(clock), counters=s.MemoryCounterStore(), clock=clock)


async def build_loaded_container(data_dir: str, clock=None, seed_excluded_terms: bool = True) -> Container:
    c = build_memory_container(clock)
    await load_dataset(c, data_dir)
    if seed_excluded_terms and not await c.excluded_terms.list():
        for t in DEFAULT_EXCLUDED_TERMS:
            await c.excluded_terms.add(ExcludedTerm(term=t, added_at=c.clock.now()))
    return c
