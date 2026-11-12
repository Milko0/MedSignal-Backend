"""Background worker (separate process): daily shortage poll now; the Mongo -> Redis projector is added by the team.

Run:  python -m app.worker
"""
import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.application.services.alert_dispatcher import AlertDispatcher
from app.application.services.ingredient_resolver import IngredientResolver
from app.application.use_cases.ingestion.poll_shortages import PollShortages
from app.core.config import get_settings
from app.infrastructure.container_factory import build_container
from app.infrastructure.external.http import HttpFetcher
from app.infrastructure.external.openfda_client import OpenFdaFeeds
from app.infrastructure.external.rxnorm_client import RxNavClient
from app.infrastructure.external.rxnorm_normalizer import RxNormNormalizer

log = logging.getLogger("medsignal.worker")


async def main() -> None:
    logging.basicConfig(level="INFO")
    settings = get_settings()
    c = await build_container(settings)
    fda = HttpFetcher(settings.openfda_requests_per_second, settings.http_max_retries, settings.http_timeout_seconds)
    rx = HttpFetcher(settings.rxnorm_requests_per_second, settings.http_max_retries, settings.http_timeout_seconds)
    normalizer = RxNormNormalizer(RxNavClient(settings, rx), settings.cache_dir)
    resolver = IngredientResolver(normalizer, c.rx_concepts, c.ingredients, c.name_map, c.clock)
    dispatcher = AlertDispatcher(c.follows, c.alerts, c.users, c.clock)
    poll = PollShortages(OpenFdaFeeds(settings, fda), c.shortages, c.products, resolver, c.shortage_status,
                         dispatcher, c.ingestion_runs, c.clock)

    async def job() -> None:
        run = await poll.execute()
        log.info("shortage poll: %s records, %s", run.records_loaded, run.stats)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(job, "cron", hour=3, minute=0, id="poll_shortages")
    scheduler.start()
    log.info("Worker started. TODO(team): run the MongoDB change-stream projector.")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
