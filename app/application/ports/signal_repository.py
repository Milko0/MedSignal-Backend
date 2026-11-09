"""Port: Precomputed quarterly signals."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime  # noqa: F401
from typing import AsyncIterator  # noqa: F401


class SignalRepository(ABC):
    @abstractmethod
    async def upsert_many(self, signals: list[dict]) -> int: ...

    @abstractmethod
    async def list(self, filters: dict, page: int, page_size: int) -> tuple[list[dict], int]: ...

    @abstractmethod
    async def top_for_drug(self, rxcui: str, limit: int = 5) -> list[dict]: ...

    @abstractmethod
    async def emerging(self, quarter: str, limit: int = 20) -> list[dict]: ...

