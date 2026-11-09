"""Port: Drug dictionary (RxNorm cache)."""
from abc import ABC, abstractmethod
from datetime import datetime  # noqa: F401
from typing import AsyncIterator  # noqa: F401


class DrugRepository(ABC):
    @abstractmethod
    async def get(self, rxcui: str) -> dict | None: ...

    @abstractmethod
    async def search(self, text: str, limit: int = 10) -> list[dict]: ...

    @abstractmethod
    async def class_members(self, class_id: str, route: str | None, dosage_form: str | None) -> list[dict]: ...

