"""Parsers for RxNav JSON. RxNav returns {} when nothing is found and scores as strings: every read checks keys."""
from app.application.ingestion.transformers.common import to_float
from app.domain.entities.drug import DrugClass
from app.domain.entities.enums import MatchMethod, Tty
from app.domain.entities.name_mapping import NameCandidate
from app.domain.entities.rx_concept import RxConcept


def parse_properties(raw: dict) -> RxConcept | None:
    props = (raw or {}).get("properties")
    if not props or not props.get("rxcui"):
        return None
    tty = props.get("tty")
    return RxConcept(rxcui=str(props["rxcui"]), tty=Tty(tty) if tty in Tty._value2member_map_ else Tty.OTHER,
                     name=props.get("name") or "")


def parse_related(raw: dict, tty: str = "IN") -> list[tuple[str, str]]:
    """(rxcui, name) of the related concepts with the given TTY."""
    out: list[tuple[str, str]] = []
    for group in ((raw or {}).get("relatedGroup") or {}).get("conceptGroup") or []:
        if group.get("tty") != tty:
            continue
        for cp in group.get("conceptProperties") or []:
            if cp.get("rxcui"):
                out.append((str(cp["rxcui"]), cp.get("name") or ""))
    return out


def parse_exact(raw: dict) -> list[str]:
    return [str(x) for x in ((raw or {}).get("idGroup") or {}).get("rxnormId") or []]


def parse_approximate(raw: dict, only_source: str | None = "RXNORM", limit: int = 5) -> list[NameCandidate]:
    """Approximate candidates come from several sources (RXNORM, DRUGBANK, MMSL...): keep only RXNORM by default."""
    seen: set[str] = set()
    out: list[NameCandidate] = []
    for c in ((raw or {}).get("approximateGroup") or {}).get("candidate") or []:
        rx = c.get("rxcui")
        if not rx or str(rx) in seen:
            continue
        if only_source and c.get("source") != only_source:
            continue
        seen.add(str(rx))
        out.append(NameCandidate(rxcui=str(rx), name=c.get("name"), source=c.get("source"),
                                 score=to_float(c.get("score")), method=MatchMethod.APPROXIMATE))
    out.sort(key=lambda c: c.score or 0.0, reverse=True)
    return out[:limit]


def parse_atc(raw: dict) -> list[DrugClass]:
    out: dict[str, DrugClass] = {}
    for info in ((raw or {}).get("rxclassDrugInfoList") or {}).get("rxclassDrugInfo") or []:
        item = info.get("rxclassMinConceptItem") or {}
        class_id = item.get("classId")
        if not class_id:
            continue
        ctype = str(item.get("classType") or "")
        level = int(ctype[-1]) if ctype.startswith("ATC") and ctype[-1].isdigit() else 4
        out[class_id] = DrugClass(class_id=class_id, name=item.get("className") or "", level=level)
    return list(out.values())


def parse_ndcs(raw: dict) -> list[str]:
    """ndcList can be {} when empty."""
    return [str(n) for n in (((raw or {}).get("ndcGroup") or {}).get("ndcList") or {}).get("ndc") or []]
