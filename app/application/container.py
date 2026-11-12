"""Everything the use cases need, bundled. The API and the worker each build ONE container at start-up.

The reference build (infrastructure/memory) fills it with in-memory adapters. The database build fills the same
fields with the MongoDB and Redis adapters. Use cases never know which one they get.
"""
from dataclasses import dataclass

from app.application.ports.alert_store import AlertStore
from app.application.ports.clock import Clock
from app.application.ports.counter_store import CounterStore
from app.application.ports.excluded_term_repository import ExcludedTermRepository
from app.application.ports.follow_store import FollowStore
from app.application.ports.ingestion_run_repository import IngestionRunRepository
from app.application.ports.ingredient_repository import IngredientRepository
from app.application.ports.label_repository import LabelRepository
from app.application.ports.name_map_repository import NameMapRepository
from app.application.ports.product_repository import ProductRepository
from app.application.ports.recall_repository import RecallRepository
from app.application.ports.report_repository import ReportRepository
from app.application.ports.rx_concept_repository import RxConceptRepository
from app.application.ports.shortage_repository import ShortageRepository
from app.application.ports.shortage_status_store import ShortageStatusStore
from app.application.ports.signal_repository import SignalRepository
from app.application.ports.user_repository import UserRepository


@dataclass
class Container:
    ingredients: IngredientRepository
    rx_concepts: RxConceptRepository
    products: ProductRepository
    labels: LabelRepository
    shortages: ShortageRepository
    recalls: RecallRepository
    name_map: NameMapRepository
    reports: ReportRepository
    signals: SignalRepository
    users: UserRepository
    excluded_terms: ExcludedTermRepository
    ingestion_runs: IngestionRunRepository
    shortage_status: ShortageStatusStore
    follows: FollowStore
    alerts: AlertStore
    counters: CounterStore
    clock: Clock
