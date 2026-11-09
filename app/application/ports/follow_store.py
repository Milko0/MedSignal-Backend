"""Port: Redis follows:{userId} and followers:{rxcui} sets (many-to-many)."""
from abc import ABC, abstractmethod
from datetime import datetime  # noqa: F401
from typing import AsyncIterator  # noqa: F401


class FollowStore(ABC):
    @abstractmethod
    async def follow(self, user_id: str, rxcui: str) -> None: ...

    @abstractmethod
    async def unfollow(self, user_id: str, rxcui: str) -> None: ...

    @abstractmethod
    async def list_followed(self, user_id: str) -> set[str]: ...

    @abstractmethod
    async def followers_of(self, rxcui: str) -> set[str]: ...

    @abstractmethod
    async def is_following(self, user_id: str, rxcui: str) -> bool: ...

