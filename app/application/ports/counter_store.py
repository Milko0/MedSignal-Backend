"""Port: key-value: live (ingredient, reaction, quarter) counters, SET from a recount, never incremented."""
from abc import ABC, abstractmethod


class CounterStore(ABC):
    @abstractmethod
    async def set_count(self, ingredient_rxcui: str, reaction: str, quarter: str, value: int) -> None: ...

    @abstractmethod
    async def get_count(self, ingredient_rxcui: str, reaction: str, quarter: str) -> int | None: ...
