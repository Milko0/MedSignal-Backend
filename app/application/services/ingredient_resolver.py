"""Resolves product rxcuis and drug names to ingredients, caching every answer.

Rules (plan 6.4): a harmonised product rxcui maps through RxNav to its ingredient(s); an EXACT name match is
accepted; an APPROXIMATE match is only stored as a candidate and never feeds signals until a person accepts it.
"""
import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Iterable

from app.application.ingestion.resolution import NameResolution
from app.application.ingestion.transformers.common import unique
from app.application.ports.drug_normalizer import DrugNormalizer
from app.application.ports.ingredient_repository import IngredientRepository
from app.application.ports.name_map_repository import NameMapRepository
from app.application.ports.rx_concept_repository import RxConceptRepository
from app.domain.entities.enums import KeyType, LinkStatus, MatchMethod
from app.domain.entities.name_mapping import NameMapping
from app.domain.entities.rx_concept import RxConcept

log = logging.getLogger("medsignal.resolver")


async def run_bounded(items: list, work: Callable[[object], Awaitable], concurrency: int, label: str) -> list:
    """Runs work(item) for every item with at most `concurrency` in flight; logs progress for long batches."""
    if not items:
        return []
    sem = asyncio.Semaphore(max(1, concurrency))
    done = 0
    started = time.monotonic()
    step = max(200, len(items) // 20)

    async def one(item):
        nonlocal done
        async with sem:
            result = await work(item)
        done += 1
        if len(items) >= 200 and (done % step == 0 or done == len(items)):
            rate = done / max(time.monotonic() - started, 1e-6)
            left = (len(items) - done) / rate if rate else 0
            log.info("%s: %d/%d (%.0f%%), %.1f/s, ~%d min left", label, done, len(items),
                     100 * done / len(items), rate, left // 60)
        return result

    return await asyncio.gather(*(one(i) for i in items))


class IngredientResolver:
    def __init__(self, normalizer: DrugNormalizer, rx_concepts: RxConceptRepository,
                 ingredients: IngredientRepository, name_map: NameMapRepository, clock, concurrency: int = 1) -> None:
        self.concurrency = concurrency
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
        missing = [rx for rx in wanted if rx not in cached]
        self.stats["rxcui_lookups"] += len(missing)

        async def lookup(rx: str) -> RxConcept:
            # a miss is remembered (empty ingredients) so it is not asked again
            return await self.normalizer.concept(rx) or RxConcept(rxcui=rx)

        new_concepts = await run_bounded(missing, lookup, self.concurrency, "product rxcuis")
        for concept in new_concepts:
            result[concept.rxcui] = concept.ingredient_rxcuis
        ingredient_ids = unique(i for c in new_concepts for i in c.ingredient_rxcuis)
        unknown = [i for i in ingredient_ids if await self.ingredients.get(i) is None]
        new_drugs = [d for d in await run_bounded(unknown, self.normalizer.ingredient, self.concurrency, "ingredients") if d]
        if new_concepts:
            await self.rx_concepts.upsert_many(new_concepts)
        if new_drugs:
            await self.ingredients.upsert_many(new_drugs)
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
        missing = [n for n in wanted if n not in existing]
        fresh: list[NameMapping] = await run_bounded(
            missing, lambda n: self._resolve_one(n, key_type), self.concurrency, f"names ({key_type.value})")
        for n, m in zip(missing, fresh, strict=True):
            existing[n] = m
        if fresh:
            await self.name_map.upsert_many(fresh)
        return {n: to_resolution(m) for n, m in existing.items()}


def to_resolution(m: NameMapping) -> NameResolution:
    usable = bool(m.ingredient_rxcuis) and (
        m.method is MatchMethod.EXACT or (m.method is MatchMethod.APPROXIMATE and m.status is LinkStatus.ACCEPTED))
    return NameResolution(method=m.method, ingredient_rxcuis=list(m.ingredient_rxcuis), usable=usable)
