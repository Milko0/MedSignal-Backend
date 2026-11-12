"""FR-04, FR-05: precomputed signals filtered by quarter, drug, reaction and minimum reports."""
from app.application.dtos.common import PageRequest, page_meta
from app.application.dtos.signals import SignalList, SignalRow
from app.application.ports.ingredient_repository import IngredientRepository
from app.application.ports.report_repository import ReportRepository
from app.application.ports.signal_repository import SignalRepository
from app.domain.entities.signal import SafetySignal
from app.domain.value_objects.reaction_term import normalize_reaction


async def to_rows(signals: list[SafetySignal], ingredients: IngredientRepository,
                  signal_repo: SignalRepository) -> list[SignalRow]:
    drugs = {d.rxcui: d for d in await ingredients.get_many(sorted({s.ingredient_rxcui for s in signals}))}
    rows = []
    for s in signals:
        d = drugs.get(s.ingredient_rxcui)
        rows.append(SignalRow(
            rxcui=s.ingredient_rxcui, drug=d.name if d else s.ingredient_rxcui, reaction=s.reaction_term,
            quarter=s.quarter, reports=s.a, a=s.a, b=s.b, c=s.c, d=s.d, prr=round(s.prr, 3),
            ci_lower=round(s.ci_lower, 3), chi_square=round(s.chi_square, 2), is_signal=s.is_signal,
            is_emerging=s.is_emerging, label_match=s.label_match.value,
            trend=[round(x, 2) for x in await signal_repo.trend(s.ingredient_rxcui, s.reaction_term)]))
    return rows


class ListSignals:
    def __init__(self, signals: SignalRepository, ingredients: IngredientRepository, reports: ReportRepository) -> None:
        self.signals, self.ingredients, self.reports = signals, ingredients, reports

    async def execute(self, quarter: str | None, rxcui: str | None = None, reaction: str | None = None,
                      min_reports: int = 20, only_signals: bool = True, page: PageRequest | None = None) -> SignalList:
        page = page or PageRequest()
        quarter = quarter or await self.signals.latest_quarter()
        if quarter is None:
            return SignalList(items=[], **page_meta(0, page))
        found, total = await self.signals.search(
            quarter, rxcui, normalize_reaction(reaction) if reaction else None, min_reports, only_signals, False,
            page.skip, page.limit)
        return SignalList(items=await to_rows(found, self.ingredients, self.signals), **page_meta(total, page),
                          quarter=quarter,
                          match_coverage=round(await self.reports.match_coverage(quarter), 3))
