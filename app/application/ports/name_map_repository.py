"""Port: auditable drug name -> ingredient resolutions."""
from abc import ABC, abstractmethod

from app.domain.entities.enums import KeyType, LinkStatus
from app.domain.entities.name_mapping import NameMapping


class NameMapRepository(ABC):
    @abstractmethod
    async def get(self, key_type: KeyType, normalized: str) -> NameMapping | None: ...

    @abstractmethod
    async def get_many(self, key_type: KeyType, normalized: list[str]) -> dict[str, NameMapping]: ...

    @abstractmethod
    async def upsert_many(self, mappings: list[NameMapping]) -> int: ...

    @abstractmethod
    async def list(self, status: LinkStatus | None = None, skip: int = 0, limit: int = 100) -> list[NameMapping]: ...
