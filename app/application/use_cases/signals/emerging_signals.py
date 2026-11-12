"""FR-06: pairs whose latest PRR is clearly above the previous quarters."""
from app.application.dtos.signals import SignalList
from app.application.ports.ingredient_repository import IngredientRepository
from app.application.ports.report_repository import ReportRepository
from app.application.ports.signal_repository import SignalRepository
from app.application.use_cases.signals.list_signals import to_rows


class EmergingSignals:
    def __init__(self, signals: SignalRepository, ingredients: IngredientRepository, reports: ReportRepository) -> None:
        self.signals, self.ingredients, self.reports = signals, ingredients, reports

    async def execute(self, quarter: str | None = None, min_reports: int = 3, limit: int = 50) -> SignalList:
        quarter = quarter or await self.signals.latest_quarter()
        if quarter is None:
            return SignalList(items=[], total=0)
        found, total = await self.signals.search(quarter, None, None, min_reports, True, True, 0, limit)
        return SignalList(items=await to_rows(found, self.ingredients, self.signals), total=total, quarter=quarter,
                          match_coverage=round(await self.reports.match_coverage(quarter), 3))
