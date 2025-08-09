# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.repo.recurring_ops import due_recurring, bump_next_run
from app.repo.records import add_operation

def _ensure_naive(dt: datetime) -> datetime:
    """Приводим любое время к naive UTC (tzinfo=None)."""
    if dt.tzinfo is not None:
        # переводим в UTC и отбрасываем tzinfo
        return dt.astimezone(tz=None).replace(tzinfo=None)
    return dt

def _next_from_period(now: datetime, period: str, hour: int | None, minute: int | None) -> datetime:
    """
    Считает следующее срабатывание. Все времена — naive UTC.
    Поддержанные периоды: daily, weekly, monthly. (как было)
    """
    now = now.replace(second=0, microsecond=0)
    h = int(hour or 9)
    m = int(minute or 0)

    if period == "daily":
        candidate = now.replace(hour=h, minute=m)
        if candidate <= now:
            candidate = candidate + timedelta(days=1)
        return candidate

    if period == "weekly":
        # day-of-week у нас хранится в БД, но упрощённо — отталкиваемся от следующего дня
        candidate = now.replace(hour=h, minute=m) + timedelta(days=7)
        return candidate

    if period == "monthly":
        # грубая логика: +30 дней (как и было в старом скелете)
        candidate = now.replace(hour=h, minute=m) + timedelta(days=30)
        return candidate

    # fallback: через сутки
    return now + timedelta(days=1)

async def generate_due_operations(session: AsyncSession, now: datetime) -> int:
    """
    Создаёт операции для всех просроченных recurring и двигает next_run.
    Все сравнения и записи — в naive UTC, чтобы совпадать с TIMESTAMP WITHOUT TIME ZONE.
    """
    now = _ensure_naive(now)

    recs = await due_recurring(session, now)  # отдаёт все, у кого next_run <= now
    created = 0

    for r in recs:
        # создаём операцию
        await add_operation(
            session=session,
            user_id=r.user_id,
            amount=r.amount,
            category=r.category,
            description=r.description or f"[recurring:{r.id}]",
            op_type=r.op_type,
        )
        created += 1

        # двигаем next_run вперёд (naive UTC)
        next_run = _next_from_period(now, r.period, r.hour, r.minute)
        await bump_next_run(session, r.id, next_run)

    return created
