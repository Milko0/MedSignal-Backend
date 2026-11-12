"""Resolves product rxcuis and drug names to ingredients, caching every answer.

Rules (plan 6.4): a harmonised product rxcui maps through RxNav to its ingredient(s); an EXACT name match is
accepted; an APPROXIMATE match is only stored as a candidate and never feeds signals until a person accepts it.
"""
from collections.abc import Iterable

from app.application.ingestion.resolution import NameResolution
from app.application.ingestion.transformers.common import unique
from app.application.ports.drug_normalizer import DrugNormalizer
from app.application.ports.ingredient_repository import IngredientRepository
from app.application.ports.name_map_repository import NameMapRepository
from app.application.ports.rx_concept_repository import RxConceptRepository
from app.domain.entities.enums import KeyType, LinkStatus, MatchMethod
from app.domain.entities.name_mapping import NameMapping
from app.domain.entities.rx_concept import RxConcept


class IngredientResolver:
    def __init__(self, normalizer: DrugNormalizer, rx_concepts: RxConceptRepository,
                 ingredients: IngredientRepository, name_map: NameMapRepository, clock) -> None:
        self.normalizer = normalizer
        self.rx_concepts = rx_concepts
        self.ingredients = ingredients
        self.name_map = name_map
        self.clock = clock
        self.stats = {"rxcui_lookups": 0, "rxcui_cached": 0, "names_exact": 0, "names_approximate": 0,
                      "names_unmatched": 0, "names_cached": 0}

    async def resolve_products(self, rxcuis: Iterable[str]) -> dict[str, list[str]]:
        wanted = unique(str(r) for r in rxcuis if r)
        cached = await self.rx_concepts.get_many(wanted)
        result = {rx: c.ingredient_rxcuis for rx, c in cached.items()}
        self.stats["rxcui_cached"] += len(cached)
        new_concepts: list[RxConcept] = []
        new_drugs = {}
        for rx in wanted:
            if rx in cached:
                continue
            self.stats["rxcui_lookups"] += 1
            concept = await self.normalizer.concept(rx)
            if concept is None:
                concept = RxConcept(rxcui=rx)  # remember the miss so it is not asked again
            new_concepts.append(concept)
            result[rx] = concept.ingredient_rxcuis
            for ing in concept.ingredient_rxcuis:
                if ing not in new_drugs and await self.ingredients.get(ing) is None:
                    drug = await self.normalizer.ingredient(ing)
                    if drug:
                        new_drugs[ing] = drug
        if new_concepts:
            await self.rx_concepts.upsert_many(new_concepts)
        if new_drugs:
            await self.ingredients.upsert_many(list(new_drugs.values()))
        return result

    async def _resolve_one(self, name: str, key_type: KeyType) -> NameMapping:
        now = self.clock.now()
        exact = await self.normalizer.exact(name)
        if exact:
            by_product = await self.resolve_products(exact)
            ingredients = unique(i for rx in exact for i in by_product.get(rx, []))
            if ingredients:
                self.stats["names_exact"] += 1
                return NameMapping(key_type=key_type, raw=name, normalized=name, status=LinkStatus.ACCEPTED,
                                   method=MatchMethod.EXACT, ingredient_rxcuis=ingredients, updated_at=now)
        candidates = await self.normalizer.approximate(name)
        if candidates:
            self.stats["names_approximate"] += 1
            return NameMapping(key_type=key_type, raw=name, normalized=name, candidates=candidates,
                               status=LinkStatus.CANDIDATE, method=MatchMethod.APPROXIMATE, updated_at=now)
        self.stats["names_unmatched"] += 1
        return NameMapping(key_type=key_type, raw=name, normalized=name, updated_at=now)

    async def resolve_names(self, names: Iterable[str], key_type: KeyType = KeyType.ACTIVESUBSTANCE) -> dict[str, NameResolution]:
        wanted = unique(names)
        existing = await self.name_map.get_many(key_type, wanted)
        self.stats["names_cached"] += len(existing)
        fresh: list[NameMapping] = []
        for n in wanted:
            if n not in existing:
                m = await self._resolve_one(n, key_type)
                fresh.append(m)
                existing[n] = m
        if fresh:
            await self.name_map.upsert_many(fresh)
        return {n: to_resolution(m) for n, m in existing.items()}


def to_resolution(m: NameMapping) -> NameResolution:
    usable = bool(m.ingredient_rxcuis) and (
        m.method is MatchMethod.EXACT or (m.method is MatchMethod.APPROXIMATE and m.status is LinkStatus.ACCEPTED))
    return NameResolution(method=m.method, ingredient_rxcuis=list(m.ingredient_rxcuis), usable=usable)
