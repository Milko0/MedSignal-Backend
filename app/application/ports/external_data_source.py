"""Port: openFDA / DailyMed feeds."""
from abc import ABC, abstractmethod
from datetime import datetime  # noqa: F401
from typing import AsyncIterator  # noqa: F401


class ExternalDataSource(ABC):
    @abstractmethod
    async def fetch_shortages(self) -> list[dict]: ...

    @abstractmethod
    async def fetch_recalls(self, since: str | None = None) -> list[dict]: ...

    @abstractmethod
    async def fetch_label(self, set_id: str) -> dict | None: ...

