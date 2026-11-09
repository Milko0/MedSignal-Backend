"""Separate process: scheduler (daily shortage poll) + change-stream projector (Mongo -> Redis).

Run:  python -m app.worker
Kept out of the API workers so jobs do not run once per uvicorn worker.
"""
import asyncio
import logging

from app.infrastructure.scheduling.jobs import build_scheduler

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("medsignal.worker")


async def main() -> None:
    scheduler = build_scheduler()
    scheduler.start()
    log.info("worker started (skeleton): scheduler running, change-stream projector not wired yet")
    # TODO: asyncio.create_task(change_stream_projector.run(...))
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
