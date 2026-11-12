"""STORAGE_BACKEND=databases: the Container whose ports are the MongoDB and Redis adapters.

MongoDB holds every document (source of truth for reports, signals, catalog, users). Redis holds only live,
key-value state: follows, alerts, shortage summaries, counters and revoked tokens (docs/PORT_CONTRACT.md).
"""
import logging

from app.application.container import Container
from app.core.config import Settings
from app.domain.entities.excluded_term import ExcludedTerm
from app.infrastructure.clock import SystemClock
from app.infrastructure.memory.factory import DEFAULT_EXCLUDED_TERMS
from app.infrastructure.mongodb.client import create_mongo_client
from app.infrastructure.mongodb.indexes import ensure_indexes
from app.infrastructure.mongodb.repositories.catalog_repositories import (
    MongoLabelRepository,
    MongoNameMapRepository,
    MongoProductRepository,
    MongoRxConceptRepository,
)
from app.infrastructure.mongodb.repositories.excluded_term_repository import MongoExcludedTermRepository
from app.infrastructure.mongodb.repositories.ingestion_run_repository import MongoIngestionRunRepository
from app.infrastructure.mongodb.repositories.ingredient_repository import MongoIngredientRepository
from app.infrastructure.mongodb.repositories.recall_repository import MongoRecallRepository
from app.infrastructure.mongodb.repositories.report_repository import MongoReportRepository
from app.infrastructure.mongodb.repositories.shortage_repository import MongoShortageRepository
from app.infrastructure.mongodb.repositories.signal_repository import MongoSignalRepository
from app.infrastructure.mongodb.repositories.user_repository import MongoUserRepository
from app.infrastructure.redis.client import create_redis_client
from app.infrastructure.redis.stores.alert_store import RedisAlertStore
from app.infrastructure.redis.stores.counter_store import RedisCounterStore
from app.infrastructure.redis.stores.follow_store import RedisFollowStore
from app.infrastructure.redis.stores.revoked_token_store import RedisRevokedTokenStore
from app.infrastructure.redis.stores.shortage_status_store import RedisShortageStatusStore

log = logging.getLogger("medsignal.storage")


def create_database_container(db, redis, clock=None) -> Container:
    """Wires the adapters around an open database handle and Redis client (used by the app and by the tests)."""
    clock = clock or SystemClock()
    return Container(
        ingredients=MongoIngredientRepository(db), rx_concepts=MongoRxConceptRepository(db),
        products=MongoProductRepository(db), labels=MongoLabelRepository(db), shortages=MongoShortageRepository(db),
        recalls=MongoRecallRepository(db), name_map=MongoNameMapRepository(db), reports=MongoReportRepository(db),
        signals=MongoSignalRepository(db), users=MongoUserRepository(db),
        excluded_terms=MongoExcludedTermRepository(db), ingestion_runs=MongoIngestionRunRepository(db),
        shortage_status=RedisShortageStatusStore(redis), follows=RedisFollowStore(redis),
        alerts=RedisAlertStore(redis, clock), counters=RedisCounterStore(redis),
        revoked_tokens=RedisRevokedTokenStore(redis, clock), clock=clock)


async def build_database_container(settings: Settings, clock=None) -> Container:
    """Connects, fails fast if a database is down, creates the indexes (idempotent) and seeds the default
    excluded terms on an empty database."""
    mongo = create_mongo_client(settings)
    redis = create_redis_client(settings)
    try:
        await mongo.admin.command("ping")
        await redis.ping()
    except Exception as exc:
        raise RuntimeError(f"STORAGE_BACKEND=databases but a database is unreachable ({settings.mongo_uri}, "
                           f"{settings.redis_url or settings.redis_sentinels}): {exc}") from exc
    db = mongo[settings.mongo_db]
    await ensure_indexes(db)
    c = create_database_container(db, redis, clock)
    if not await c.excluded_terms.list():
        for t in DEFAULT_EXCLUDED_TERMS:
            await c.excluded_terms.add(ExcludedTerm(term=t, added_at=c.clock.now()))
    log.info("MongoDB %s/%s and Redis connected; %d reports", settings.mongo_uri, settings.mongo_db,
             await c.reports.count())
    return c
