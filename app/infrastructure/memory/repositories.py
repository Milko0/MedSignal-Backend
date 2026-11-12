"""Reference adapters: every repository port implemented in memory. They define the behaviour the MongoDB adapters
must reproduce (the conformance suite in tests/conformance runs the same assertions against every adapter)."""
from collections import Counter

from app.application.ports.excluded_term_repository import ExcludedTermRepository
from app.application.ports.ingestion_run_repository import IngestionRunRepository
from app.application.ports.ingredient_repository import IngredientRepository
from app.application.ports.label_repository import LabelRepository
from app.application.ports.name_map_repository import NameMapRepository
from app.application.ports.product_repository import ProductRepository
from app.application.ports.recall_repository import RecallRepository
from app.application.ports.report_repository import ReportRepository
from app.application.ports.rx_concept_repository import RxConceptRepository
from app.application.ports.shortage_repository import ShortageRepository
from app.application.ports.signal_repository import SignalRepository
from app.application.ports.user_repository import UserRepository
from app.domain.entities.drug import Drug
from app.domain.entities.enums import KeyType, LinkStatus, ProductType, RoleFilter
from app.domain.entities.excluded_term import ExcludedTerm
from app.domain.entities.ingestion_run import IngestionRun
from app.domain.entities.label import DrugLabel
from app.domain.entities.name_mapping import NameMapping
from app.domain.entities.product import Product
from app.domain.entities.recall import Recall
from app.domain.entities.report import AdverseReport
from app.domain.entities.rx_concept import RxConcept
from app.domain.entities.shortage import ShortageEvent, ShortageRecord
from app.domain.entities.signal import SafetySignal
from app.domain.entities.user import User
from app.domain.exceptions import AlreadyExistsError
from app.domain.services.name_search import best_matches, normalize_query
from app.domain.value_objects.pair_counts import PairCounts


class MemoryIngredientRepository(IngredientRepository):
    def __init__(self) -> None:
        self._d: dict[str, Drug] = {}

    def all_items(self):
        return list(self._d.values())

    async def get(self, rxcui):
        return self._d.get(rxcui)

    async def get_many(self, rxcuis):
        return [self._d[r] for r in rxcuis if r in self._d]

    async def search(self, query, limit=10):
        q = normalize_query(query)
        if not q:
            return []
        candidates = ((d.rxcui, d.name, [d.name, *d.synonyms, *d.brand_names]) for d in self._d.values())
        return [(self._d[rx], text, score) for rx, text, score in best_matches(q, candidates, limit)]

    async def list_by_class(self, class_id):
        return [d for d in self._d.values() if any(c.class_id == class_id for c in d.atc)]

    async def upsert_many(self, drugs):
        for d in drugs:
            self._d[d.rxcui] = d
        return len(drugs)

    async def count(self):
        return len(self._d)


class MemoryRxConceptRepository(RxConceptRepository):
    def __init__(self) -> None:
        self._d: dict[str, RxConcept] = {}

    def all_items(self):
        return list(self._d.values())

    async def get_many(self, rxcuis):
        return {r: self._d[r] for r in rxcuis if r in self._d}

    async def upsert_many(self, concepts):
        for c in concepts:
            self._d[c.rxcui] = c
        return len(concepts)

    async def all_ingredient_map(self):
        return {r: c.ingredient_rxcuis for r, c in self._d.items()}


class MemoryProductRepository(ProductRepository):
    def __init__(self) -> None:
        self._d: dict[str, Product] = {}

    def all_items(self):
        return list(self._d.values())

    async def upsert_many(self, products):
        for p in products:
            self._d[p.product_ndc] = p
        return len(products)

    async def get(self, product_ndc):
        return self._d.get(product_ndc)

    async def find_by_ingredient(self, ingredient_rxcui, route=None, dosage_form=None):
        out = []
        for p in self._d.values():
            if ingredient_rxcui not in p.ingredient_rxcuis:
                continue
            if route and route.upper() not in p.routes:
                continue
            if dosage_form and p.dosage_form != dosage_form.upper():
                continue
            out.append(p)
        return out

    async def product_ingredient_map(self):
        return {p.product_ndc: p.ingredient_rxcuis for p in self._d.values() if p.ingredient_rxcuis}


class MemoryLabelRepository(LabelRepository):
    def __init__(self) -> None:
        self._d: dict[str, DrugLabel] = {}

    def all_items(self):
        return list(self._d.values())

    async def upsert_many(self, labels):
        for lb in labels:
            self._d[lb.set_id] = lb
        return len(labels)

    async def get(self, set_id):
        return self._d.get(set_id)

    async def find_by_ingredient(self, ingredient_rxcui, product_type: ProductType | None = None):
        return [lb for lb in self._d.values() if ingredient_rxcui in lb.ingredient_rxcuis
                and (product_type is None or lb.product_type is product_type)]

    async def count(self):
        return len(self._d)


class MemoryShortageRepository(ShortageRepository):
    def __init__(self) -> None:
        self._current: dict[str, ShortageRecord] = {}
        self._events: list[ShortageEvent] = []

    def all_items(self):
        return list(self._current.values())

    def all_events(self):
        return list(self._events)

    async def current_by_package(self):
        return dict(self._current)

    async def replace_current(self, records):
        self._current = {r.package_ndc: r for r in records}
        return len(records)

    async def add_events(self, events):
        self._events.extend(events)
        return len(events)

    async def find_by_ingredient(self, ingredient_rxcui):
        return [r for r in self._current.values() if ingredient_rxcui in r.ingredient_rxcuis]

    async def events_for_ingredient(self, ingredient_rxcui, limit=100):
        ev = [e for e in self._events if ingredient_rxcui in e.ingredient_rxcuis]
        return sorted(ev, key=lambda e: e.at, reverse=True)[:limit]


class MemoryRecallRepository(RecallRepository):
    def __init__(self) -> None:
        self._d: dict[str, Recall] = {}

    def all_items(self):
        return list(self._d.values())

    async def upsert_many(self, recalls):
        for r in recalls:
            self._d[r.recall_number] = r
        return len(recalls)

    async def all(self):
        return list(self._d.values())

    async def find_by_ingredient(self, ingredient_rxcui, accepted_only=True):
        out = []
        for r in self._d.values():
            if r.link.status is LinkStatus.ACCEPTED and ingredient_rxcui in r.link.ingredient_rxcuis or not accepted_only and any(c.rxcui == ingredient_rxcui for c in r.link.candidates):
                out.append(r)
        return out

    async def linked_share(self):
        if not self._d:
            return 0.0
        return sum(1 for r in self._d.values() if r.link.status is LinkStatus.ACCEPTED) / len(self._d)


class MemoryNameMapRepository(NameMapRepository):
    def __init__(self) -> None:
        self._d: dict[tuple[KeyType, str], NameMapping] = {}

    def all_items(self):
        return list(self._d.values())

    async def get(self, key_type, normalized):
        return self._d.get((key_type, normalized))

    async def get_many(self, key_type, normalized):
        return {n: self._d[(key_type, n)] for n in normalized if (key_type, n) in self._d}

    async def upsert_many(self, mappings):
        for m in mappings:
            self._d[(m.key_type, m.normalized)] = m
        return len(mappings)

    async def list(self, status=None, skip=0, limit=100):
        items = [m for m in self._d.values() if status is None or m.status is status]
        return items[skip:skip + limit]


_AGE_ORDER = ["0-17", "18-44", "45-64", "65-74", "75+", "UNKNOWN"]


class MemoryReportRepository(ReportRepository):
    def __init__(self) -> None:
        self._d: dict[str, AdverseReport] = {}

    def all_items(self):
        return list(self._d.values())

    async def upsert_many(self, reports):
        for r in reports:
            old = self._d.get(r.report_id)
            if old is None or r.version >= old.version:
                self._d[r.report_id] = r
        return len(reports)

    async def get(self, report_id):
        return self._d.get(report_id)

    async def delete(self, report_id):
        return self._d.pop(report_id, None) is not None

    async def count(self):
        return len(self._d)

    async def quarters(self):
        return sorted({r.quarter for r in self._d.values()})

    async def delete_quarter(self, quarter):
        ids = [k for k, r in self._d.items() if r.quarter == quarter]
        for k in ids:
            del self._d[k]
        return len(ids)

    async def pair_counts(self, quarter, role_filter, excluded_terms):
        pc = PairCounts()
        per_drug: Counter = Counter()
        per_reaction: Counter = Counter()
        per_pair: Counter = Counter()
        for r in self._d.values():
            if r.quarter != quarter:
                continue
            drugs = r.suspect_ingredient_ids if role_filter is RoleFilter.SUSPECT else r.all_ingredient_ids
            reactions = [t for t in r.reaction_pts if t not in excluded_terms]
            pc.total += 1  # every report of the quarter is in the universe, even without a resolved drug
            for d in drugs:
                per_drug[d] += 1
            for t in reactions:
                per_reaction[t] += 1
            for d in drugs:
                for t in reactions:
                    per_pair[(d, t)] += 1
        pc.per_drug, pc.per_reaction, pc.per_pair = dict(per_drug), dict(per_reaction), dict(per_pair)
        return pc

    async def top_reactions(self, ingredient_rxcui, limit, role_filter, excluded_terms):
        c: Counter = Counter()
        for r in self._d.values():
            ids = r.suspect_ingredient_ids if role_filter is RoleFilter.SUSPECT else r.all_ingredient_ids
            if ingredient_rxcui in ids:
                c.update(t for t in r.reaction_pts if t not in excluded_terms)
        return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]

    async def monthly_trend(self, ingredient_rxcui, reactions, months):
        mine = [r for r in self._d.values() if ingredient_rxcui in r.suspect_ingredient_ids]
        if not mine or not reactions:
            return []
        last = max(r.receive_date for r in mine)
        y, m = last.year, last.month
        window = []
        for _ in range(months):
            window.append(f"{y:04d}-{m:02d}")
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        window.reverse()
        counts: Counter = Counter()
        for r in mine:
            key = f"{r.receive_date.year:04d}-{r.receive_date.month:02d}"
            for t in r.reaction_pts:
                if t in reactions:
                    counts[(key, t)] += 1
        return [(mo, t, counts[(mo, t)]) for mo in window for t in reactions]

    async def list_for_pair(self, ingredient_rxcui, reaction, skip, limit):
        hits = [r for r in self._d.values() if ingredient_rxcui in r.suspect_ingredient_ids and reaction in r.reaction_pts]
        hits.sort(key=lambda r: (r.receive_date, r.report_id), reverse=True)
        return hits[skip:skip + limit], len(hits)

    async def statistics(self, group_by, ingredient_rxcui, quarter):
        c: Counter = Counter()
        for r in self._d.values():
            if quarter and r.quarter != quarter:
                continue
            if ingredient_rxcui and ingredient_rxcui not in r.suspect_ingredient_ids:
                continue
            if group_by == "age_group":
                key = r.patient.age_group.value
            elif group_by == "sex":
                key = r.patient.sex.value
            elif group_by == "country":
                key = r.country or "UNKNOWN"
            elif group_by == "seriousness":
                key = {True: "SERIOUS", False: "NON_SERIOUS"}.get(r.seriousness.serious, "UNKNOWN")
            elif group_by == "report_type":
                key = r.report_type.value
            elif group_by == "quarter":
                key = r.quarter
            else:
                raise ValueError(f"Unknown group_by {group_by}")
            c[key] += 1
        if group_by == "age_group":
            return [(k, c[k]) for k in _AGE_ORDER if k in c]
        if group_by == "quarter":
            return sorted(c.items())
        return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))

    async def match_coverage(self, quarter=None):
        reports = [r for r in self._d.values() if quarter is None or r.quarter == quarter]
        if not reports:
            return 0.0
        return sum(1 for r in reports if r.all_ingredient_ids) / len(reports)


class MemorySignalRepository(SignalRepository):
    def __init__(self) -> None:
        self._d: dict[str, SafetySignal] = {}

    def all_items(self):
        return list(self._d.values())

    async def upsert_many(self, signals):
        for s in signals:
            self._d[s.signal_id] = s
        return len(signals)

    async def search(self, quarter, ingredient_rxcui, reaction, min_reports, only_signals, only_emerging, skip, limit):
        hits = [s for s in self._d.values() if s.quarter == quarter and s.a >= min_reports
                and (ingredient_rxcui is None or s.ingredient_rxcui == ingredient_rxcui)
                and (reaction is None or s.reaction_term == reaction)
                and (not only_signals or s.is_signal) and (not only_emerging or s.is_emerging)]
        hits.sort(key=lambda s: (-s.prr, -s.a, s.signal_id))
        return hits[skip:skip + limit], len(hits)

    def _history(self, ingredient_rxcui, reaction):
        return sorted((s for s in self._d.values() if s.ingredient_rxcui == ingredient_rxcui and s.reaction_term == reaction),
                      key=lambda s: s.quarter)

    async def previous_prrs(self, ingredient_rxcui, reaction, quarter, n=4):
        prev = [s.prr for s in self._history(ingredient_rxcui, reaction) if s.quarter < quarter]
        return prev[-n:]

    async def trend(self, ingredient_rxcui, reaction, n=6):
        return [s.prr for s in self._history(ingredient_rxcui, reaction)][-n:]

    async def signal_count(self, ingredient_rxcui, quarter):
        return sum(1 for s in self._d.values() if s.ingredient_rxcui == ingredient_rxcui and s.quarter == quarter and s.is_signal)

    async def latest_quarter(self):
        return max((s.quarter for s in self._d.values()), default=None)

    async def delete_quarter(self, quarter):
        ids = [k for k, s in self._d.items() if s.quarter == quarter]
        for k in ids:
            del self._d[k]
        return len(ids)


class MemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._d: dict[str, User] = {}

    def all_items(self):
        return list(self._d.values())

    async def create(self, user):
        if await self.get_by_username_or_email(user.username) or await self.get_by_username_or_email(user.email):
            raise AlreadyExistsError("Username or email already registered")
        self._d[user.user_id] = user
        return user

    async def get_by_id(self, user_id):
        return self._d.get(user_id)

    async def get_by_username_or_email(self, value):
        v = value.lower()
        return next((u for u in self._d.values() if u.username.lower() == v or u.email.lower() == v), None)

    async def update(self, user):
        self._d[user.user_id] = user

    async def delete(self, user_id):
        return self._d.pop(user_id, None) is not None

    async def list(self, skip, limit):
        return list(self._d.values())[skip:skip + limit]


class MemoryExcludedTermRepository(ExcludedTermRepository):
    def __init__(self) -> None:
        self._d: dict[str, ExcludedTerm] = {}

    def all_items(self):
        return list(self._d.values())

    async def list(self):
        return list(self._d.values())

    async def add(self, term):
        self._d[term.term] = term

    async def remove(self, term):
        return self._d.pop(term, None) is not None


class MemoryIngestionRunRepository(IngestionRunRepository):
    def __init__(self) -> None:
        self._d: dict[str, IngestionRun] = {}

    def all_items(self):
        return list(self._d.values())

    async def add(self, run):
        self._d[run.run_id] = run

    async def update(self, run):
        self._d[run.run_id] = run

    async def list(self, skip=0, limit=50):
        runs = sorted(self._d.values(), key=lambda r: r.started_at, reverse=True)
        return runs[skip:skip + limit]
