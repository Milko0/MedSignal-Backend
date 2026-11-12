"""Brand names of an ingredient, taken from the NDC products that contain ONLY that ingredient.

Combination products are skipped: "Advil PM" must not become a brand of ibuprofen alone. A brand equal to the
generic name ("Ibuprofen", "ATORVASTATIN CALCIUM") is not a brand. Spellings are merged case-insensitively and
the most frequent spelling is kept; brands are ordered by how many products carry them.
"""
from collections import Counter, defaultdict
from collections.abc import Iterable

from app.domain.entities.product import Product

MAX_BRANDS = 10

# Store-brand OTC names are descriptions, not brands ("Pain Relief", "Childrens Pain and Fever 160 MG")
GENERIC_WORDS = frozenset("""
AND OF THE FOR WITH PLUS EXTRA STRENGTH MAXIMUM REGULAR RAPID FAST ACTING RELEASE IMMEDIATE EXTENDED DELAYED ER XR SR
CR DR IR ODT ORAL SOLUTION SUSPENSION TABLET TABLETS CAPSULE CAPSULES LIQUID GELS SOFTGELS CAPLETS CHEWABLE MINIS
INJECTION CREAM GEL OINTMENT DROPS SPRAY PATCH CHILDRENS CHILDREN INFANTS INFANT JUNIOR ADULT KIDS DR PAIN RELIEF
RELIEVER FEVER ARTHRITIS HEADACHE COLD FLU ALLERGY SLEEP NIGHTTIME DAYTIME DYE FREE SUGAR MG ML MCG HCL
HYDROCHLORIDE SODIUM POTASSIUM CALCIUM HR HOUR NON-ASPIRIN NON ASPIRIN ACID REDUCER MENSTRUAL MULTI SYMPTOM
GOOD SENSE LEADER EQUATE BASIC CARE BERKLEY JENSEN TOPCARE CVS WALGREENS KIRKLAND MEDIQUE THOMPSON UNISHIELD GREEN
GUARD GENEXA CAREONE RITE AID SUNMARK HEALTH MART QUALITY CHOICE HEB MEIJER KROGER AMAZON BASICS
""".split())  # noqa: SIM905 - a word list is easier to read and extend


def _key(text: str) -> str:
    return " ".join(text.upper().replace("'", "").split())


def _is_descriptive(brand_key: str, generic_key: str) -> bool:
    """True when the 'brand' only repeats the generic name and/or generic words (or doses)."""
    generic_tokens = set(generic_key.split())
    tokens = brand_key.split()
    if generic_tokens & set(tokens) - GENERIC_WORDS:
        return True                               # "Childrens Ibuprofen", "Metformin hydrochloride ER"
    return all(t in GENERIC_WORDS or t.replace(".", "").isdigit() for t in tokens)


def brand_names_by_ingredient(products: Iterable[Product], max_brands: int = MAX_BRANDS) -> dict[str, list[str]]:
    spellings: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for p in products:
        if len(p.ingredient_rxcuis) != 1 or not p.brand_name:
            continue
        brand = " ".join(p.brand_name.split())
        key = _key(brand)
        generic = _key(p.generic_name or "")
        names = " ".join([generic, *(_key(a.name) for a in p.active_ingredients)])
        if not key or _is_descriptive(key, names):
            continue
        spellings[p.ingredient_rxcuis[0]][key][brand] += 1
    out: dict[str, list[str]] = {}
    for ingredient, by_key in spellings.items():
        ranked = sorted(by_key.items(), key=lambda kv: (-sum(kv[1].values()), kv[0]))
        out[ingredient] = [c.most_common(1)[0][0] for _, c in ranked[:max_brands]]
    return out
