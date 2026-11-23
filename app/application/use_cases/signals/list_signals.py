"""FR-04, FR-05: precomputed signals filtered by quarter, drug, reaction and minimum reports."""
from app.application.dtos.common import PageRequest, page_meta
from app.application.dtos.signals import SignalList, SignalRow
from app.application.ports.ingredient_repository import IngredientRepository
from app.application.ports.report_repository import ReportRepository
from app.application.ports.signal_repository import SignalRepository
from app.application.services.shortage_status_reader import ShortageStatusReader
from app.domain.entities.enums import ShortageStatus
from app.domain.entities.signal import SafetySignal
from app.domain.value_objects.reaction_term import reaction_search_pattern


async def to_rows(signals: list[SafetySignal], ingredients: IngredientRepository,
                  signal_repo: SignalRepository, shortage: ShortageStatusReader | None = None) -> list[SignalRow]:
    drugs = {d.rxcui: d for d in await ingredients.get_many(sorted({s.ingredient_rxcui for s in signals}))}
    status = await shortage.worst_status(s.ingredient_rxcui for s in signals) if shortage else {}
    rows = []
    for s in signals:
        d = drugs.get(s.ingredient_rxcui)
        st = status.get(s.ingredient_rxcui)
        rows.append(SignalRow(
            shortage_status=st, in_shortage=st == ShortageStatus.CURRENT.value,
            rxcui=s.ingredient_rxcui, drug=d.name if d else s.ingredient_rxcui, reaction=s.reaction_term,
            quarter=s.quarter, reports=s.a, a=s.a, b=s.b, c=s.c, d=s.d, prr=round(s.prr, 3),
            ci_lower=round(s.ci_lower, 3), chi_square=round(s.chi_square, 2), is_signal=s.is_signal,
            is_emerging=s.is_emerging, label_match=s.label_match.value,
            trend=[round(x, 2) for x in await signal_repo.trend(s.ingredient_rxcui, s.reaction_term)]))
    return rows


class ListSignals:
    def __init__(self, signals: SignalRepository, ingredients: IngredientRepository, reports: ReportRepository,
                 shortage: ShortageStatusReader | None = None) -> None:
        self.signals, self.ingredients, self.reports, self.shortage = signals, ingredients, reports, shortage

    async def execute(self, quarter: str | None, rxcui: str | None = None, reaction: str | None = None,
                      min_reports: int = 20, only_signals: bool = True, page: PageRequest | None = None) -> SignalList:
        page = page or PageRequest()
        quarter = quarter or await self.signals.latest_quarter()
        if quarter is None:
            return SignalList(items=[], **page_meta(0, page))
        # The reaction filter finds the text anywhere in the term ("device", "anemia" -> ANAEMIA)
        found, total = await self.signals.search(
            quarter, rxcui, None, min_reports, only_signals, False, page.skip, page.limit,
            reaction_contains=reaction_search_pattern(reaction) if reaction else None)
        return SignalList(items=await to_rows(found, self.ingredients, self.signals, self.shortage),
                          **page_meta(total, page),
                          quarter=quarter,
                          match_coverage=round(await self.reports.match_coverage(quarter), 3))
