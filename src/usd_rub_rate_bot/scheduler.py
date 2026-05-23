"""APScheduler wiring."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


def build_scheduler(
    job: Callable[[], Awaitable[None]],
    cron_expression: str,
) -> AsyncIOScheduler:
    """Build (but do not start) an AsyncIOScheduler with a single cron job."""

    scheduler = AsyncIOScheduler(timezone="UTC")
    trigger = CronTrigger.from_crontab(cron_expression, timezone="UTC")
    scheduler.add_job(
        job,
        trigger=trigger,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=30,
    )
    return scheduler
