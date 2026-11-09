"""MongoDB adapter for the users collection. TODO: implement the methods."""
from __future__ import annotations

from typing import AsyncIterator  # noqa: F401
from datetime import datetime  # noqa: F401

from app.application.ports.user_repository import UserRepository


class MongoUserRepository(UserRepository):
    def __init__(self, db):
        self._col = db['users']

    async def create(self, user: dict) -> dict:
        raise NotImplementedError

    async def get_by_id(self, user_id: str) -> dict | None:
        raise NotImplementedError

    async def get_by_login(self, login: str) -> dict | None:
        raise NotImplementedError

    async def update(self, user_id: str, fields: dict) -> dict | None:
        raise NotImplementedError

    async def delete(self, user_id: str) -> bool:
        raise NotImplementedError

    async def list(self, page: int, page_size: int) -> list[dict]:
        raise NotImplementedError

