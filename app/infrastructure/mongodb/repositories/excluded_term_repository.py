"""MongoDB adapter for the excluded_terms collection. TODO: implement the methods."""
from __future__ import annotations

from typing import AsyncIterator  # noqa: F401
from datetime import datetime  # noqa: F401

from app.application.ports.excluded_term_repository import ExcludedTermRepository


class MongoExcludedTermRepository(ExcludedTermRepository):
    def __init__(self, db):
        self._col = db['excluded_terms']

    async def list(self) -> list[str]:
        raise NotImplementedError

    async def add(self, term: str) -> None:
        raise NotImplementedError

    async def remove(self, term: str) -> None:
        raise NotImplementedError

