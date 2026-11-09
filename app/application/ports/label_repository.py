"""Port: Drug labels and versions."""
from abc import ABC, abstractmethod
from datetime import datetime  # noqa: F401
from typing import AsyncIterator  # noqa: F401


class LabelRepository(ABC):
    @abstractmethod
    async def upsert(self, label: dict) -> None: ...

    @abstractmethod
    async def summary_for_drug(self, rxcui: str) -> dict | None: ...

    @abstractmethod
    async def adverse_text_for_drug(self, rxcui: str) -> str: ...

    @abstractmethod
    async def history(self, set_id: str) -> list[dict]: ...

