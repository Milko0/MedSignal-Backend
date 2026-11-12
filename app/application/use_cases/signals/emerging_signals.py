"""FR-06: pairs whose latest PRR is clearly above the previous quarters."""
from app.application.dtos.common import PageRequest, page_meta
from app.application.dtos.signals import SignalList
from app.application.ports.ingredient_repository import IngredientRepository
from app.application.ports.report_repository import ReportRepository
from app.application.ports.signal_repository import SignalRepository
from app.application.use_cases.signals.list_signals import to_rows


class EmergingSignals:
    def __init__(self, signals: SignalRepository, ingredients: IngredientRepository, reports: ReportRepository) -> None:
        self.signals, self.ingredients, self.reports = signals, ingredients, reports

    async def execute(self, quarter: str | None = None, min_reports: int = 3,
                      page: PageRequest | None = None) -> SignalList:
        page = page or PageRequest()
        quarter = quarter or await self.signals.latest_quarter()
        if quarter is None:
            return SignalList(items=[], **page_meta(0, page))
        found, total = await self.signals.search(quarter, None, None, min_reports, True, True, page.skip, page.limit)
        return SignalList(items=await to_rows(found, self.ingredients, self.signals), **page_meta(total, page),
                          quarter=quarter,
                          match_coverage=round(await self.reports.match_coverage(quarter), 3))
