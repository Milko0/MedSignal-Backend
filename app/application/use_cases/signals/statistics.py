"""FR-08: reports by age group, sex, country, seriousness and quarter."""
from app.application.dtos.signals import StatBucket, Statistics
from app.application.ports.report_repository import ReportRepository

GROUPS = ("age_group", "sex", "country", "seriousness", "report_type", "quarter")


class GetStatistics:
    def __init__(self, reports: ReportRepository) -> None:
        self.reports = reports

    async def execute(self, group_by: str, rxcui: str | None = None, quarter: str | None = None) -> Statistics:
        rows = await self.reports.statistics(group_by, rxcui, quarter)
        return Statistics(group_by=group_by, buckets=[StatBucket(group=g, value=v) for g, v in rows])
