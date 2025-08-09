# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from datetime import datetime
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_sessionmaker
from app.services.reminders import fire_due_reminders
from app.services.recurring import generate_due_operations

log = logging.getLogger(__name__)

def _utc_naive_now() -> datetime:
    # Всегда возвращаем UTC без tzinfo, чтобы сравнение с колонками
    # TIMESTAMP WITHOUT TIME ZONE не падало.
    return datetime.utcnow().replace(microsecond=0)

async def start_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    @scheduler.scheduled_job("interval", seconds=60, id="reminders_tick")
    async def tick_reminders() -> None:
        # naive UTC
        now = _utc_naive_now()
        async with async_sessionmaker() as session:  # type: AsyncSession
            fired = await fire_due_reminders(session, now)
        if fired:
            log.debug("reminders fired=%s", fired)

    @scheduler.scheduled_job("interval", seconds=60, id="recurring_tick")
    async def tick_recurring() -> None:
        # naive UTC
        now = _utc_naive_now()
        async with async_sessionmaker() as session:  # type: AsyncSession
            created = await generate_due_operations(session, now)
        if created:
            log.debug("recurring created=%s", created)

    scheduler.start()
    log.info("Scheduler started")
    return scheduler
