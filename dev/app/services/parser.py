# app/services/reports.py
# Агрегации для отчётов

from __future__ import annotations
from typing import Optional
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.repo.records import get_operations_range, aggregate_by_category

async def report_summary(
    session: AsyncSession,
    user_db_id: int,
    start: date,
    end: date,
) -> dict[str, float]:
    ops = await get_operations_range(session, user_db_id, start, end)
    return await aggregate_by_category(ops)

async def spent_on_category(
    session: AsyncSession,
    user_db_id: int,
    start: date,
    end: date,
    category_name: str,
) -> float:
    """
    Сумма по категории за период: расходы отрицательные → берём модуль только для расходов.
    """
    ops = await get_operations_range(session, user_db_id, start, end)
    total = 0.0
    for o in ops:
        if (o.category or "").lower() == category_name.lower() and o.type == "expense":
            total += abs(float(o.amount))
    return round(total, 2)
