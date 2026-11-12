"""Port: logs of ingestion runs (FR-21)."""
from abc import ABC, abstractmethod

from app.domain.entities.ingestion_run import IngestionRun


class IngestionRunRepository(ABC):
    @abstractmethod
    async def add(self, run: IngestionRun) -> None: ...

    @abstractmethod
    async def update(self, run: IngestionRun) -> None: ...

    @abstractmethod
    async def list(self, skip: int = 0, limit: int = 50) -> list[IngestionRun]: ...
