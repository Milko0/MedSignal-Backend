"""Port: key-value: many-to-many users <-> ingredients (source of truth)."""
from abc import ABC, abstractmethod


class FollowStore(ABC):
    @abstractmethod
    async def follow(self, user_id: str, ingredient_rxcui: str) -> None: ...

    @abstractmethod
    async def unfollow(self, user_id: str, ingredient_rxcui: str) -> None: ...

    @abstractmethod
    async def list_followed(self, user_id: str) -> set[str]: ...

    @abstractmethod
    async def followers(self, ingredient_rxcui: str) -> set[str]: ...

    @abstractmethod
    async def is_following(self, user_id: str, ingredient_rxcui: str) -> bool: ...
