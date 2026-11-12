"""Reference collections built by ingestion: rx_concepts, products, labels, name_map."""
from app.application.ports.label_repository import LabelRepository
from app.application.ports.name_map_repository import NameMapRepository
from app.application.ports.product_repository import ProductRepository
from app.application.ports.rx_concept_repository import RxConceptRepository
from app.domain.entities.label import DrugLabel
from app.domain.entities.name_mapping import NameMapping
from app.domain.entities.product import Product
from app.domain.entities.rx_concept import RxConcept
from app.infrastructure.mongodb.documents import from_doc, replace_many, to_doc


class MongoRxConceptRepository(RxConceptRepository):
    """`rx_concepts`, `_id` = rxcui. An empty ingredient list is a remembered RxNav miss and is kept."""

    def __init__(self, db) -> None:
        self.col = db["rx_concepts"]

    async def get_many(self, rxcuis):
        return {d["_id"]: from_doc(RxConcept, d, "rxcui") async for d in self.col.find({"_id": {"$in": list(rxcuis)}})}

    async def upsert_many(self, concepts):
        return await replace_many(self.col, [to_doc(c, "rxcui") for c in concepts])

    async def all_ingredient_map(self):
        return {d["_id"]: d.get("ingredient_rxcuis", []) async for d in self.col.find({}, {"ingredient_rxcuis": 1})}


class MongoProductRepository(ProductRepository):
    """`products`, `_id` = product_ndc, packages embedded."""

    def __init__(self, db) -> None:
        self.col = db["products"]

    async def upsert_many(self, products):
        return await replace_many(self.col, [to_doc(p, "product_ndc") for p in products])

    async def get(self, product_ndc):
        return from_doc(Product, await self.col.find_one({"_id": product_ndc}), "product_ndc")

    async def find_by_ingredient(self, ingredient_rxcui, route=None, dosage_form=None):
        query: dict = {"ingredient_rxcuis": ingredient_rxcui}
        if route:
            query["routes"] = route.upper()
        if dosage_form:
            query["dosage_form"] = dosage_form.upper()
        return [from_doc(Product, d, "product_ndc") async for d in self.col.find(query)]

    async def product_ingredient_map(self):
        cursor = self.col.find({"ingredient_rxcuis.0": {"$exists": True}}, {"ingredient_rxcuis": 1})
        return {d["_id"]: d["ingredient_rxcuis"] async for d in cursor}


class MongoLabelRepository(LabelRepository):
    """`labels`, `_id` = set_id (lower case)."""

    def __init__(self, db) -> None:
        self.col = db["labels"]

    async def upsert_many(self, labels):
        return await replace_many(self.col, [to_doc(lb, "set_id") for lb in labels])

    async def get(self, set_id):
        return from_doc(DrugLabel, await self.col.find_one({"_id": set_id}), "set_id")

    async def find_by_ingredient(self, ingredient_rxcui, product_type=None):
        query: dict = {"ingredient_rxcuis": ingredient_rxcui}
        if product_type is not None:
            query["product_type"] = product_type.value
        return [from_doc(DrugLabel, d, "set_id") async for d in self.col.find(query)]

    async def count(self):
        return await self.col.count_documents({})


def _map_id(key_type, normalized: str) -> str:
    return f"{key_type}|{normalized}"


class MongoNameMapRepository(NameMapRepository):
    """`name_map`, `_id` = "KEY_TYPE|normalized" (the compound natural key as one string)."""

    def __init__(self, db) -> None:
        self.col = db["name_map"]

    async def get(self, key_type, normalized):
        return from_doc(NameMapping, await self.col.find_one({"_id": _map_id(key_type, normalized)}))

    async def get_many(self, key_type, normalized):
        ids = [_map_id(key_type, n) for n in normalized]
        found = {d["normalized"]: from_doc(NameMapping, d) async for d in self.col.find({"_id": {"$in": ids}})}
        return {n: found[n] for n in normalized if n in found}

    async def upsert_many(self, mappings):
        return await replace_many(self.col, [to_doc(m, _id=_map_id(m.key_type, m.normalized)) for m in mappings])

    async def list(self, status=None, skip=0, limit=100):
        query = {"status": status.value} if status is not None else {}
        return [from_doc(NameMapping, d) async for d in self.col.find(query, sort=[("_id", 1)], skip=skip,
                                                                      limit=limit)]
