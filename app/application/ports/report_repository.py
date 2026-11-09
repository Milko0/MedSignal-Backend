"""Port: FAERS reports (MongoDB reports collection)."""
from abc import ABC, abstractmethod
from datetime import datetime  # noqa: F401
from typing import AsyncIterator  # noqa: F401


class ReportRepository(ABC):
    @abstractmethod
    async def upsert_many(self, reports: list[dict]) -> int: ...

    @abstractmethod
    async def get(self, report_id: str) -> dict | None: ...

    @abstractmethod
    async def list_for_signal(self, rxcui: str, reaction: str, quarter: str, limit: int = 20, skip: int = 0) -> list[dict]: ...

    @abstractmethod
    async def contingency_counts(self, quarter: str) -> AsyncIterator[dict]: ...

    @abstractmethod
    async def stats_by(self, group_by: str, filters: dict) -> list[dict]: ...

