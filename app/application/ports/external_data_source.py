"""Port: raw feeds of the external sources (dictionaries exactly as the API returns them)."""
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import date


class ShortageFeed(ABC):
    @abstractmethod
    def fetch_shortages(self) -> AsyncIterator[dict]: ...

    @abstractmethod
    async def last_updated(self) -> str | None: ...


class NdcFeed(ABC):
    @abstractmethod
    def fetch_products(self, limit: int | None = None) -> AsyncIterator[dict]: ...


class LabelFeed(ABC):
    @abstractmethod
    def fetch_labels(self, limit: int | None = None, since: date | None = None) -> AsyncIterator[dict]:
        """Labels; with `since`, only those whose effective date is on or after that day."""


class RecallFeed(ABC):
    @abstractmethod
    def fetch_recalls(self, limit: int | None = None, since: date | None = None) -> AsyncIterator[dict]:
        """Recalls; with `since`, only those reported on or after that day."""


class ReportFeed(ABC):
    @abstractmethod
    def read_bulk_file(self, path: str) -> AsyncIterator[dict]: ...
