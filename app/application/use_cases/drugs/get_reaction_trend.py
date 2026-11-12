"""FR-03: monthly trend of the most reported reactions."""
from app.application.dtos.drugs import TrendPoint
from app.application.ports.excluded_term_repository import ExcludedTermRepository
from app.application.ports.report_repository import ReportRepository
from app.domain.entities.enums import RoleFilter


class GetReactionTrend:
    def __init__(self, reports: ReportRepository, excluded_terms: ExcludedTermRepository) -> None:
        self.reports, self.excluded_terms = reports, excluded_terms

    async def execute(self, rxcui: str, months: int = 12, top: int = 3) -> list[TrendPoint]:
        excluded = await self.excluded_terms.as_set()
        reactions = [r for r, _ in await self.reports.top_reactions(rxcui, top, RoleFilter.SUSPECT, excluded)]
        rows = await self.reports.monthly_trend(rxcui, reactions, months)
        return [TrendPoint(month=m, reaction=r, reports=n) for m, r, n in rows]
