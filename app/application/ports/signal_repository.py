"""Port: precomputed quarterly signals."""
from abc import ABC, abstractmethod

from app.domain.entities.signal import SafetySignal


class SignalRepository(ABC):
    @abstractmethod
    async def upsert_many(self, signals: list[SafetySignal]) -> int: ...

    @abstractmethod
    async def search(self, quarter: str, ingredient_rxcui: str | None, reaction: str | None, min_reports: int,
                     only_signals: bool, only_emerging: bool, skip: int, limit: int) -> tuple[list[SafetySignal], int]: ...

    @abstractmethod
    async def previous_prrs(self, ingredient_rxcui: str, reaction: str, quarter: str, n: int = 4) -> list[float]: ...

    @abstractmethod
    async def trend(self, ingredient_rxcui: str, reaction: str, n: int = 6) -> list[float]: ...

    @abstractmethod
    async def signal_count(self, ingredient_rxcui: str, quarter: str) -> int:
        """Pairs that meet the Evans criteria for the ingredient in the quarter."""

    @abstractmethod
    async def latest_quarter(self) -> str | None: ...
