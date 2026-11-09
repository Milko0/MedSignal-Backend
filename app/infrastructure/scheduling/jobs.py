"""Scheduled jobs (APScheduler). FR-28: daily shortage poll that stores every status change."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler


async def poll_shortages_job() -> None:
    raise NotImplementedError("wire PollShortages here")


def build_scheduler() -> AsyncIOScheduler:
    sched = AsyncIOScheduler()
    sched.add_job(poll_shortages_job, "cron", hour=3, minute=0, id="poll_shortages")
    return sched
