"""Port: Ingestion logs (FR-21)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime  # noqa: F401
from typing import AsyncIterator  # noqa: F401


class IngestionRunRepository(ABC):
    @abstractmethod
    async def start(self, kind: str) -> str: ...

    @abstractmethod
    async def finish(self, run_id: str, records: int, errors: list[str]) -> None: ...

    @abstractmethod
    async def list(self, limit: int = 50) -> list[dict]: ...

