"""MongoDB adapter for the signals collection. TODO: implement the methods."""
from __future__ import annotations

from typing import AsyncIterator  # noqa: F401
from datetime import datetime  # noqa: F401

from app.application.ports.signal_repository import SignalRepository


class MongoSignalRepository(SignalRepository):
    def __init__(self, db):
        self._col = db['signals']

    async def upsert_many(self, signals: list[dict]) -> int:
        raise NotImplementedError

    async def list(self, filters: dict, page: int, page_size: int) -> tuple[list[dict], int]:
        raise NotImplementedError

    async def top_for_drug(self, rxcui: str, limit: int = 5) -> list[dict]:
        raise NotImplementedError

    async def emerging(self, quarter: str, limit: int = 20) -> list[dict]:
        raise NotImplementedError

