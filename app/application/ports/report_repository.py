"""Port: adverse event reports and the read models built from them."""
from abc import ABC, abstractmethod

from app.domain.entities.enums import RoleFilter
from app.domain.entities.report import AdverseReport
from app.domain.value_objects.pair_counts import PairCounts


class ReportRepository(ABC):
    @abstractmethod
    async def upsert_many(self, reports: list[AdverseReport]) -> int:
        """Upsert by report_id keeping only the HIGHEST version of a case."""

    @abstractmethod
    async def get(self, report_id: str) -> AdverseReport | None: ...

    @abstractmethod
    async def delete(self, report_id: str) -> bool: ...

    @abstractmethod
    async def delete_quarter(self, quarter: str) -> int:
        """Deletes every report of the quarter (rolling window). Returns how many. Mongo: index {quarter: 1}."""

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def quarters(self) -> list[str]: ...

    @abstractmethod
    async def pair_counts(self, quarter: str, role_filter: RoleFilter, excluded_terms: set[str]) -> PairCounts:
        """Counts for every 2x2 table of the quarter (Mongo: one aggregation pipeline)."""

    @abstractmethod
    async def top_reactions(self, ingredient_rxcui: str, limit: int, role_filter: RoleFilter,
                            excluded_terms: set[str]) -> list[tuple[str, int]]: ...

    @abstractmethod
    async def monthly_trend(self, ingredient_rxcui: str, reactions: list[str], months: int) -> list[tuple[str, str, int]]:
        """(YYYY-MM, reaction PT, reports) for suspect reports."""

    @abstractmethod
    async def list_for_pair(self, ingredient_rxcui: str, reaction: str, skip: int, limit: int) -> tuple[list[AdverseReport], int]: ...

    @abstractmethod
    async def statistics(self, group_by: str, ingredient_rxcui: str | None, quarter: str | None) -> list[tuple[str, int]]: ...

    @abstractmethod
    async def match_coverage(self, quarter: str | None = None) -> float:
        """Share of reports with at least one resolved ingredient (suspect or concomitant)."""
