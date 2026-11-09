"""MongoDB adapter for the reports collection. TODO: implement the methods."""
from typing import AsyncIterator  # noqa: F401
from datetime import datetime  # noqa: F401

from app.application.ports.report_repository import ReportRepository


class MongoReportRepository(ReportRepository):
    def __init__(self, db):
        self._col = db['reports']

    async def upsert_many(self, reports: list[dict]) -> int:
        raise NotImplementedError

    async def get(self, report_id: str) -> dict | None:
        raise NotImplementedError

    async def list_for_signal(self, rxcui: str, reaction: str, quarter: str, limit: int = 20, skip: int = 0) -> list[dict]:
        raise NotImplementedError

    async def contingency_counts(self, quarter: str) -> AsyncIterator[dict]:
        raise NotImplementedError

    async def stats_by(self, group_by: str, filters: dict) -> list[dict]:
        raise NotImplementedError

