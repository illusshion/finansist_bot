# app/services/search.py
# Поиск по операциям: по подстроке в описании/категории + период.

from __future__ import annotations
from datetime import date, datetime
from typing import List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operation import Operation


async def search_operations(
    session: AsyncSession,
    user_db_id: int,
    query: str,
    start: date,
    end: date,
) -> list[Operation]:
    q = (query or "").strip().lower()
    if not q:
        return []

    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())

    stmt = (
        select(Operation)
        .where(
            and_(
                Operation.user_id == user_db_id,
                Operation.created_at >= start_dt,
                Operation.created_at <= end_dt,
            )
        )
        .order_by(Operation.created_at.asc())
    )
    res = await session.execute(stmt)
    ops = list(res.scalars().all())

    # Фильтруем в питоне — чтобы не заморачиваться с ILIKE/indices на старте
    out: list[Operation] = []
    for o in ops:
        cat = (o.category or "").lower()
        desc = (o.description or "").lower()
        if q in cat or q in desc:
            out.append(o)
    return out
