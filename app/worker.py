"""Background worker (separate process from the API).

- daily shortage poll (FR-28), 03:00;
- with STORAGE_BACKEND=databases: the MongoDB -> Redis change-stream projector (signal counters and alerts,
  shortage summaries). On a standalone mongod (no change streams) it runs Reconcile (FR-27) every 10 minutes instead;
  on a replica set Reconcile still runs hourly as a safety net.

Run:  py -m app.worker
"""
import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.application.services.alert_dispatcher import AlertDispatcher
from app.application.services.ingredient_resolver import IngredientResolver
from app.application.use_cases.ingestion.poll_shortages import PollShortages
from app.application.use_cases.sync.project_change_event import ProjectChangeEvent
from app.application.use_cases.sync.reconcile import Reconcile
from app.core.config import get_settings
from app.infrastructure.container_factory import build_container
from app.infrastructure.external.http import HttpFetcher
from app.infrastructure.external.openfda_client import OpenFdaFeeds
from app.infrastructure.external.rxnorm_client import RxNavClient
from app.infrastructure.external.rxnorm_normalizer import RxNormNormalizer

log = logging.getLogger("medsignal.worker")


async def main() -> None:
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    c = await build_container(settings)
    fda = HttpFetcher(settings.openfda_requests_per_second, settings.http_max_retries, settings.http_timeout_seconds)
    rx = HttpFetcher(settings.rxnorm_requests_per_second, settings.http_max_retries, settings.http_timeout_seconds)
    normalizer = RxNormNormalizer(RxNavClient(settings, rx), settings.cache_dir)
    resolver = IngredientResolver(normalizer, c.rx_concepts, c.ingredients, c.name_map, c.clock,
                                  concurrency=settings.rxnorm_concurrency)
    dispatcher = AlertDispatcher(c.follows, c.alerts, c.users, c.clock)
    poll = PollShortages(OpenFdaFeeds(settings, fda), c.shortages, c.products, resolver, c.shortage_status,
                         dispatcher, c.ingestion_runs, c.clock)
    reconcile = Reconcile(c.ingredients, c.shortages, c.shortage_status, c.clock)

    async def poll_job() -> None:
        run = await poll.execute()
        log.info("shortage poll: %s records, %s", run.records_loaded, run.stats)

    async def reconcile_job() -> None:
        log.info("reconcile: %s", await reconcile.execute())

    scheduler = AsyncIOScheduler()
    scheduler.add_job(poll_job, "cron", hour=3, minute=0, id="poll_shortages")
    tasks = []
    if settings.storage_backend == "databases":
        from app.infrastructure.mongodb.client import create_mongo_client
        from app.infrastructure.sync.change_stream_projector import ChangeStreamProjector, supports_change_streams
        from app.infrastructure.sync.checkpoint_store import CheckpointStore

        mongo = create_mongo_client(settings)
        db = mongo[settings.mongo_db]
        if await supports_change_streams(mongo):
            project = ProjectChangeEvent(c.shortages, c.shortage_status, c.counters, dispatcher, c.clock)
            tasks.append(asyncio.create_task(ChangeStreamProjector(db, project, CheckpointStore(db)).run()))
            scheduler.add_job(reconcile_job, "interval", hours=1, id="reconcile")
        else:
            log.warning("MongoDB is not a replica set: no change streams. Running Reconcile every 10 minutes "
                        "(signal alerts need the replica set).")
            scheduler.add_job(reconcile_job, "interval", minutes=10, id="reconcile")
    scheduler.start()
    log.info("Worker started (%s storage)", settings.storage_backend)
    if tasks:
        await asyncio.gather(*tasks)          # a crash of the projector stops the worker visibly
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
