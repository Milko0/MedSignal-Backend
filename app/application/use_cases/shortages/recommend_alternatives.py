"""FR-10: substitutes for a drug in shortage. Same ingredient first, then same ATC class, always route and form aware."""
from collections import Counter

from app.application.dtos.shortages import AlternativeRow, AlternativesData
from app.application.ports.ingredient_repository import IngredientRepository
from app.application.ports.product_repository import ProductRepository
from app.application.ports.recall_repository import RecallRepository
from app.application.ports.shortage_repository import ShortageRepository
from app.application.ports.signal_repository import SignalRepository
from app.domain.entities.enums import MatchType, ShortageStatus
from app.domain.entities.product import Product
from app.domain.entities.shortage import SubstituteSuggestion
from app.domain.exceptions import NotFoundError
from app.domain.services.alternative_ranker import (
    profile_from_signal_count,
    rank_alternatives,
)


class RecommendAlternatives:
    def __init__(self, ingredients: IngredientRepository, products: ProductRepository,
                 shortages: ShortageRepository, recalls: RecallRepository, signals: SignalRepository) -> None:
        self.ingredients, self.products, self.shortages = ingredients, products, shortages
        self.recalls, self.signals = recalls, signals

    async def _suggestion(self, drug, match_type, products: list[Product], in_shortage: set[str],
                          form: str | None, routes: list[str], quarter: str | None) -> SubstituteSuggestion | None:
        available = [p for p in products if p.product_ndc not in in_shortage]
        if not available:
            return None
        n_signals = await self.signals.signal_count(drug.rxcui, quarter) if quarter else 0
        return SubstituteSuggestion(
            match_type=match_type, ingredient_rxcui=drug.rxcui, name=drug.name, dosage_form=form, routes=routes,
            recall_count=len(await self.recalls.find_by_ingredient(drug.rxcui, accepted_only=True)),
            signal_profile=profile_from_signal_count(n_signals), products_available=len(available))

    async def execute(self, rxcui: str, dosage_form: str | None = None, route: str | None = None) -> AlternativesData:
        drug = await self.ingredients.get(rxcui)
        if drug is None:
            raise NotFoundError(f"Unknown ingredient {rxcui}")
        records = await self.shortages.find_by_ingredient(rxcui)
        current = [r for r in records if r.status is ShortageStatus.CURRENT]
        # target form and route: the filter, otherwise the ones that are actually in shortage
        form = dosage_form.upper() if dosage_form else (
            Counter(r.dosage_form for r in current if r.dosage_form).most_common(1) or [(None, 0)])[0][0]
        routes = [route.upper()] if route else sorted({x for r in current for x in r.routes})
        route_filters = routes or [None]

        in_shortage = {r.product_ndc for r in (await self.shortages.current_by_package()).values()
                       if r.status is ShortageStatus.CURRENT and r.product_ndc}
        quarter = await self.signals.latest_quarter()

        candidates: list[SubstituteSuggestion] = []
        own: dict[str, Product] = {}
        for rt in route_filters:
            for p in await self.products.find_by_ingredient(rxcui, rt, form):
                own[p.product_ndc] = p
        s = await self._suggestion(drug, MatchType.SAME_INGREDIENT, list(own.values()), in_shortage, form, routes, quarter)
        if s:
            candidates.append(s)

        seen = {rxcui}
        for cls in drug.atc:
            for other in await self.ingredients.list_by_class(cls.class_id):
                if other.rxcui in seen:
                    continue
                seen.add(other.rxcui)
                prods: dict[str, Product] = {}
                for rt in route_filters:
                    for p in await self.products.find_by_ingredient(other.rxcui, rt, form):
                        prods[p.product_ndc] = p
                s = await self._suggestion(other, MatchType.SAME_CLASS, list(prods.values()), in_shortage, form, routes, quarter)
                if s:
                    candidates.append(s)

        return AlternativesData(target_dosage_form=form, target_routes=routes, items=[
            AlternativeRow(match_type=c.match_type.value, rxcui=c.ingredient_rxcui, name=c.name, dosage_form=c.dosage_form,
                           routes=c.routes, recalls=c.recall_count, signal_profile=c.signal_profile.value,
                           products_available=c.products_available, rank=c.rank)
            for c in rank_alternatives(candidates)])
