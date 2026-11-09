"""Port: Non-specific reaction terms (FR-26)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime  # noqa: F401
from typing import AsyncIterator  # noqa: F401


class ExcludedTermRepository(ABC):
    @abstractmethod
    async def list(self) -> list[str]: ...

    @abstractmethod
    async def add(self, term: str) -> None: ...

    @abstractmethod
    async def remove(self, term: str) -> None: ...

