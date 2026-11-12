"""DrugNormalizer adapter over RxNav with a JSON disk cache (the same input is never asked twice)."""
import hashlib
import json
from pathlib import Path

from app.application.ingestion.transformers import rxnorm as parse
from app.application.ports.drug_normalizer import DrugNormalizer
from app.domain.entities.drug import Drug, DrugClass
from app.domain.entities.enums import Tty
from app.domain.entities.name_mapping import NameCandidate
from app.domain.entities.rx_concept import RxConcept
from app.infrastructure.external.rxnorm_client import RxNavClient


class DiskCache:
    def __init__(self, directory: str | None) -> None:
        self.dir = Path(directory) if directory else None
        if self.dir:
            self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, kind: str, key: str) -> Path:
        return self.dir / f"{kind}-{hashlib.sha1(key.encode()).hexdigest()}.json"

    def get(self, kind: str, key: str):
        if not self.dir:
            return None
        p = self._path(kind, key)
        return json.loads(p.read_text()) if p.exists() else None

    def set(self, kind: str, key: str, value) -> None:
        if self.dir:
            self._path(kind, key).write_text(json.dumps(value))


class RxNormNormalizer(DrugNormalizer):
    def __init__(self, client: RxNavClient, cache_dir: str | None = None) -> None:
        self.client, self.cache = client, DiskCache(cache_dir)

    async def _cached(self, kind: str, key: str, fetch):
        hit = self.cache.get(kind, key)
        if hit is not None:
            return hit
        value = await fetch()
        self.cache.set(kind, key, value)
        return value

    async def concept(self, rxcui):
        props = parse.parse_properties(await self._cached("props", rxcui, lambda: self.client.properties(rxcui)))
        if props is None:
            return None
        if props.tty is Tty.IN:
            ingredients = [rxcui]  # an ingredient maps to itself
        else:
            related = await self._cached("in", rxcui, lambda: self.client.related(rxcui, "IN"))
            ingredients = [rx for rx, _ in parse.parse_related(related, "IN")]
        return RxConcept(rxcui=rxcui, tty=props.tty, name=props.name, ingredient_rxcuis=ingredients)

    async def ingredient(self, rxcui):
        props = parse.parse_properties(await self._cached("props", rxcui, lambda: self.client.properties(rxcui)))
        if props is None:
            return None
        return Drug(rxcui=rxcui, name=props.name.upper(), synonyms=[], atc=await self.atc_classes(rxcui))

    async def exact(self, name):
        return parse.parse_exact(await self._cached("exact", name, lambda: self.client.rxcui_by_name(name)))

    async def approximate(self, term, max_entries=5) -> list[NameCandidate]:
        raw = await self._cached("approx", f"{term}|{max_entries}", lambda: self.client.approximate(term, max_entries))
        return parse.parse_approximate(raw, limit=max_entries)

    async def atc_classes(self, ingredient_rxcui) -> list[DrugClass]:
        return parse.parse_atc(await self._cached("atc", ingredient_rxcui, lambda: self.client.atc(ingredient_rxcui)))
