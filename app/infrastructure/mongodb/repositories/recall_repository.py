"""MongoDB adapter for the recalls collection. TODO: implement the methods."""
from typing import AsyncIterator  # noqa: F401
from datetime import datetime  # noqa: F401

from app.application.ports.recall_repository import RecallRepository


class MongoRecallRepository(RecallRepository):
    def __init__(self, db):
        self._col = db['recalls']

    async def upsert_many(self, recalls: list[dict]) -> int:
        raise NotImplementedError

    async def counts_by_class(self, rxcui: str) -> dict[str, int]:
        raise NotImplementedError

