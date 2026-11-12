"""FR-21: ingestion logs."""
from app.application.dtos.admin import IngestionRunDto
from app.application.ports.ingestion_run_repository import IngestionRunRepository


class ListIngestionRuns:
    def __init__(self, runs: IngestionRunRepository) -> None:
        self.runs = runs

    async def execute(self, skip: int = 0, limit: int = 50) -> list[IngestionRunDto]:
        return [IngestionRunDto(
            run_id=r.run_id, type=r.type.value, source=r.source, source_last_updated=r.source_last_updated,
            started_at=r.started_at.isoformat(), ended_at=r.ended_at.isoformat() if r.ended_at else None,
            records_loaded=r.records_loaded, records_skipped=r.records_skipped, errors=r.errors, stats=r.stats)
            for r in await self.runs.list(skip, limit)]
