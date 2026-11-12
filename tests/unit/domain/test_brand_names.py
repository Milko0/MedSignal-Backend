from app.application.use_cases.ingestion.attach_brand_names import AttachBrandNames
from app.domain.entities.drug import Drug
from app.domain.entities.product import ActiveIngredient, Product
from app.domain.services.brand_names import brand_names_by_ingredient


def _p(ndc, brand, generic, ingredients, actives=None):
    return Product(product_ndc=ndc, brand_name=brand, generic_name=generic, ingredient_rxcuis=ingredients,
                   active_ingredients=[ActiveIngredient(name=a) for a in (actives or [generic])])


PRODUCTS = [
    _p("1", "Ozempic", "SEMAGLUTIDE", ["S"]), _p("2", "OZEMPIC", "SEMAGLUTIDE", ["S"]),
    _p("3", "Wegovy", "SEMAGLUTIDE", ["S"]),
    _p("4", "Advil", "IBUPROFEN", ["I"]), _p("5", "Childrens Ibuprofen", "IBUPROFEN", ["I"]),
    _p("6", "good sense pain relief", "IBUPROFEN", ["I"]), _p("7", "Ibuprofen", "IBUPROFEN", ["I"]),
    _p("8", "Advil PM", "IBUPROFEN AND DIPHENHYDRAMINE", ["I", "D"], ["IBUPROFEN", "DIPHENHYDRAMINE"]),
    _p("9", "Lipitor", "ATORVASTATIN CALCIUM", ["A"], ["ATORVASTATIN CALCIUM TRIHYDRATE"]),
    _p("10", None, "ATORVASTATIN CALCIUM", ["A"]),
]


def test_brands_ranked_merged_and_filtered():
    b = brand_names_by_ingredient(PRODUCTS)
    assert b["S"] == ["Ozempic", "Wegovy"]           # spellings merged, most frequent first
    assert b["I"] == ["Advil"]                        # generic, store-brand and combination products dropped
    assert b["A"] == ["Lipitor"] and "D" not in b


async def test_attach_is_idempotent(world):
    await world.ingredients.upsert_many([Drug(rxcui="S", name="SEMAGLUTIDE")])
    uc = AttachBrandNames(world.ingredients)
    assert await uc.execute(PRODUCTS) >= 1
    assert (await world.ingredients.search("ozempic"))[0][0].rxcui == "S"     # search finds the brand
    assert await uc.execute(PRODUCTS) == 0                                     # nothing changes the second time
