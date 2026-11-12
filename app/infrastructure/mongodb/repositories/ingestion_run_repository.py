from app.application.ports.ingestion_run_repository import IngestionRunRepository
from app.domain.entities.ingestion_run import IngestionRun
from app.infrastructure.mongodb.documents import from_doc, to_doc


class MongoIngestionRunRepository(IngestionRunRepository):
    """`ingestion_runs`, `_id` = run_id, newest first on the {started_at: -1} index (FR-21)."""

    def __init__(self, db) -> None:
        self.col = db["ingestion_runs"]

    async def add(self, run):
        doc = to_doc(run, "run_id")
        await self.col.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    async def update(self, run):
        await self.add(run)

    async def list(self, skip=0, limit=50):
        cursor = self.col.find({}, sort=[("started_at", -1)], skip=skip, limit=limit)
        return [from_doc(IngestionRun, d, "run_id") async for d in cursor]
