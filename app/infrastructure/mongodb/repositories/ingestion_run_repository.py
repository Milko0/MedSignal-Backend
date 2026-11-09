"""MongoDB adapter for the ingestion_runs collection. TODO: implement the methods."""
from __future__ import annotations

from typing import AsyncIterator  # noqa: F401
from datetime import datetime  # noqa: F401

from app.application.ports.ingestion_run_repository import IngestionRunRepository


class MongoIngestionRunRepository(IngestionRunRepository):
    def __init__(self, db):
        self._col = db['ingestion_runs']

    async def start(self, kind: str) -> str:
        raise NotImplementedError

    async def finish(self, run_id: str, records: int, errors: list[str]) -> None:
        raise NotImplementedError

    async def list(self, limit: int = 50) -> list[dict]:
        raise NotImplementedError

