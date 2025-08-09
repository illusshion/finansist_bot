# app/repo/records.py
from __future__ import annotations
from datetime import datetime, date, timedelta
from collections import defaultdict
from typing import Iterable, List, Optional

from sqlalchemy import select, and_, asc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.operation import Operation

def _normalize_amount(op: Operation) -> float:
    # доходы положительные, расходы отрицательные
    sign = 1.0 if (op.type == "income") else -1.0
    return float(abs(op.amount)) * sign

async def add_operation(
    session: AsyncSession,
    user_id: int,
    amount: float,
    category: str,
    description: str | None,
    op_type: str,  # "income" | "expense"
    created_at: datetime | None = None,
) -> Operation:
    op = Operation(
        user_id=user_id,
        amount=amount,
        category=category,
        description=description,
        type=op_type,
        created_at=created_at or datetime.utcnow(),
    )
    session.add(op)
    await session.flush()
    return op

async def delete_operation(session: AsyncSession, user_id: int, op_id: int) -> bool:
    q = await session.execute(select(Operation).where(
        and_(Operation.id == op_id, Operation.user_id == user_id)
    ))
    op = q.scalar_one_or_none()
    if not op:
        return False
    await session.delete(op)
    return True

async def get_operations_range(
    session: AsyncSession,
    user_id: int,
    start: date,
    end: date,
) -> list[Operation]:
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())
    q = await session.execute(select(Operation)
                              .where(and_(
                                  Operation.user_id == user_id,
                                  Operation.created_at >= start_dt,
                                  Operation.created_at <= end_dt
                              ))
                              .order_by(asc(Operation.created_at)))
    return list(q.scalars().all())

async def aggregate_by_category(ops: Iterable[Operation]) -> dict[str, float]:
    agg: dict[str, float] = defaultdict(float)
    for o in ops:
        agg[o.category or "Прочее"] += _normalize_amount(o)
    # округление до 2 знаков
    return {k: round(v, 2) for k, v in agg.items()}

async def balance(session: AsyncSession, user_id: int) -> float:
    q = await session.execute(select(Operation).where(Operation.user_id == user_id))
    ops = list(q.scalars().all())
    inc = sum(_normalize_amount(o) for o in ops if o.type == "income")
    exp = sum(_normalize_amount(o) for o in ops if o.type == "expense")
    return round(inc + exp, 2)
