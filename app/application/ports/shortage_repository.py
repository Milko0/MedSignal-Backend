"""Port: Shortage history (source of truth for shortage:{rxcui})."""
from abc import ABC, abstractmethod
from datetime import datetime  # noqa: F401
from typing import AsyncIterator  # noqa: F401


class ShortageRepository(ABC):
    @abstractmethod
    async def append_status_change(self, record: dict) -> None: ...

    @abstractmethod
    async def latest_status(self, rxcui: str) -> dict | None: ...

    @abstractmethod
    async def history(self, rxcui: str) -> list[dict]: ...

    @abstractmethod
    async def current_counts(self, rxcuis: list[str]) -> dict[str, int]: ...

