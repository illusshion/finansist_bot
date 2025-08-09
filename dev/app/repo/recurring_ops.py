# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recurring import RecurringOp


async def due_recurring(session: AsyncSession, now: datetime) -> Sequence[RecurringOp]:
    """
    Вернёт все рекуррентные операции, у которых next_run <= now.
    В БД next_run — TIMESTAMP WITHOUT TIME ZONE, поэтому 'now' должен быть naive (tzinfo=None).
    """
    now = now.replace(tzinfo=None)  # на всякий случай
    stmt = (
        select(RecurringOp)
        .where(RecurringOp.next_run <= now)
        .order_by(RecurringOp.next_run.asc())
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def bump_next_run(session: AsyncSession, rec_id: int, next_run: datetime) -> None:
    """
    Обновляет next_run у записи RecurringOp.
    next_run записываем как naive UTC (tzinfo=None), чтобы совпадало с типом в БД.
    """
    next_run = next_run.replace(tzinfo=None, microsecond=0)
    stmt = (
        update(RecurringOp)
        .where(RecurringOp.id == rec_id)
        .values(next_run=next_run)
    )
    await session.execute(stmt)
