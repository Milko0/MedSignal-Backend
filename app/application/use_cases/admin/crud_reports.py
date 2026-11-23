"""FR-22: administrator CRUD on adverse event reports.

Signals are precomputed per quarter, so a changed report shows in the signals after the next signal run for its
quarter (ingestion), not immediately.
"""
from app.application.ports.report_repository import ReportRepository
from app.domain.entities.report import AdverseReport
from app.domain.exceptions import AlreadyExistsError, NotFoundError, ValidationRuleError


class CrudReports:
    def __init__(self, reports: ReportRepository) -> None:
        self.reports = reports

    async def list(self, skip: int, limit: int) -> list[AdverseReport]:
        return await self.reports.list(skip, limit)

    async def get(self, report_id: str) -> AdverseReport:
        report = await self.reports.get(report_id)
        if report is None:
            raise NotFoundError(f"Report {report_id} not found")
        return report

    async def create(self, report: AdverseReport) -> AdverseReport:
        if await self.reports.get(report.report_id) is not None:
            raise AlreadyExistsError(f"Report {report.report_id} already exists")
        await self.reports.upsert_many([report])
        return report

    async def update(self, report_id: str, report: AdverseReport) -> AdverseReport:
        if report.report_id != report_id:
            raise ValidationRuleError("The report_id in the body must match the URL")
        old = await self.get(report_id)
        # the repository keeps the highest version of a case: an admin edit becomes the next version
        report = report.model_copy(update={"version": max(report.version, old.version)})
        await self.reports.upsert_many([report])
        return report

    async def delete(self, report_id: str) -> None:
        if not await self.reports.delete(report_id):
            raise NotFoundError(f"Report {report_id} not found")
