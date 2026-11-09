"""MongoDB adapter for the shortages collection. TODO: implement the methods."""
from typing import AsyncIterator  # noqa: F401
from datetime import datetime  # noqa: F401

from app.application.ports.shortage_repository import ShortageRepository


class MongoShortageRepository(ShortageRepository):
    def __init__(self, db):
        self._col = db['shortages']

    async def append_status_change(self, record: dict) -> None:
        raise NotImplementedError

    async def latest_status(self, rxcui: str) -> dict | None:
        raise NotImplementedError

    async def history(self, rxcui: str) -> list[dict]:
        raise NotImplementedError

    async def current_counts(self, rxcuis: list[str]) -> dict[str, int]:
        raise NotImplementedError

