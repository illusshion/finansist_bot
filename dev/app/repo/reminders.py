# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder import Reminder


async def due_reminders(session: AsyncSession, now: datetime) -> Sequence[Reminder]:
    """
    Все напоминания, у которых when_at <= now и is_done = false.
    Колонка when_at — без таймзоны, поэтому now должен быть naïve.
    """
    stmt = (
        select(Reminder)
        .where(Reminder.when_at <= now)
        .where(Reminder.is_done.is_(False))
        .order_by(Reminder.when_at.asc())
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def mark_done(session: AsyncSession, reminder_id: int) -> None:
    """
    Пометить напоминание выполненным.
    """
    stmt = (
        update(Reminder)
        .where(Reminder.id == reminder_id)
        .values(is_done=True)
    )
    await session.execute(stmt)
