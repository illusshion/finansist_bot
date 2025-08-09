# app/services/reports.py
from __future__ import annotations
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from app.repo.records import get_operations_range

async def report_summary(
    session: AsyncSession,
    user_db_id: int,
    start: date,
    end: date,
) -> dict[str, float]:
    """
    Возвращает словарь: {категория: сумма со знаком} за период.
    Доходы > 0, расходы < 0.
    """
    ops = await get_operations_range(session, user_db_id, start, end)
    agg: dict[str, float] = {}
    for o in ops:
        sign = 1.0 if o.type == "income" else -1.0
        val = sign * float(abs(o.amount))
        cat = o.category or "Прочее"
        agg[cat] = agg.get(cat, 0.0) + val
    return {k: round(v, 2) for k, v in agg.items()}

async def spent_on_category(
    session: AsyncSession,
    user_db_id: int,
    start: date,
    end: date,
    category_name: str,
) -> float:
    """
    Сумма РАСХОДОВ по категории за период (положительное число).
    """
    ops = await get_operations_range(session, user_db_id, start, end)
    want = (category_name or "").lower()
    total = 0.0
    for o in ops:
        if o.type == "expense" and (o.category or "").lower() == want:
            total += abs(float(o.amount))
    return round(total, 2)
