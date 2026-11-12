"""Fake RxNav (dictionary based) for tests."""
from app.application.ports.drug_normalizer import DrugNormalizer
from app.domain.entities.drug import Drug, DrugClass
from app.domain.entities.enums import MatchMethod, Tty
from app.domain.entities.name_mapping import NameCandidate
from app.domain.entities.rx_concept import RxConcept
from tests.fixtures.raw import ING_NAMES, NAMES, PRODUCTS

ATC = {"5640": [DrugClass(class_id="M01AE", name="Propionic acid derivatives", level=4)],
       "7258": [DrugClass(class_id="M01AE", name="Propionic acid derivatives", level=4)],
       "161": [DrugClass(class_id="N02BE", name="Anilides", level=4)],
       "723": [DrugClass(class_id="J01CA", name="Penicillins with extended spectrum", level=4)]}
APPROX = {"PARACETAMOL'S SOMETHING": [NameCandidate(rxcui="161", name="paracetamol", source="RXNORM", score=9.1,
                                                      method=MatchMethod.APPROXIMATE)],
          "SEMAGLUTIDE INJECTION": [NameCandidate(rxcui="999999", name="semaglutide", source="RXNORM", score=13.2,
                                                    method=MatchMethod.APPROXIMATE)]}


class FakeNormalizer(DrugNormalizer):
    def __init__(self) -> None:
        self.calls = {"concept": 0, "exact": 0, "approximate": 0}

    async def concept(self, rxcui):
        self.calls["concept"] += 1
        if rxcui in PRODUCTS:
            return RxConcept(rxcui=rxcui, tty=Tty.SCD, name=f"product {rxcui}", ingredient_rxcuis=[PRODUCTS[rxcui]])
        if rxcui in ING_NAMES:
            return RxConcept(rxcui=rxcui, tty=Tty.IN, name=ING_NAMES[rxcui], ingredient_rxcuis=[rxcui])
        return None

    async def ingredient(self, rxcui):
        if rxcui in ING_NAMES:
            return Drug(rxcui=rxcui, name=ING_NAMES[rxcui], brand_names=[ING_NAMES[rxcui].title() + "X"],
                        atc=ATC.get(rxcui, []))
        return None

    async def exact(self, name):
        self.calls["exact"] += 1
        return [NAMES[name]] if name in NAMES else []

    async def approximate(self, term, max_entries=5):
        self.calls["approximate"] += 1
        return APPROX.get(term.upper(), [])

    async def atc_classes(self, ingredient_rxcui):
        return ATC.get(ingredient_rxcui, [])
