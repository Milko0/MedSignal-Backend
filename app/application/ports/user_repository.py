"""Port: Users."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime  # noqa: F401
from typing import AsyncIterator  # noqa: F401


class UserRepository(ABC):
    @abstractmethod
    async def create(self, user: dict) -> dict: ...

    @abstractmethod
    async def get_by_id(self, user_id: str) -> dict | None: ...

    @abstractmethod
    async def get_by_login(self, login: str) -> dict | None: ...

    @abstractmethod
    async def update(self, user_id: str, fields: dict) -> dict | None: ...

    @abstractmethod
    async def delete(self, user_id: str) -> bool: ...

    @abstractmethod
    async def list(self, page: int, page_size: int) -> list[dict]: ...

