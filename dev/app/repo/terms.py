# app/repo/terms.py
from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.term import UserTerm

async def get_user_term(session: AsyncSession, user_tg_id: int, term: str) -> str | None:
    q = await session.execute(
        select(UserTerm).where(UserTerm.user_tg_id == user_tg_id, UserTerm.term == term)
    )
    row = q.scalar_one_or_none()
    return row.category if row else None

async def save_user_term_db(session: AsyncSession, user_tg_id: int, term: str, category: str) -> None:
    # upsert-поведение: если есть — обновим
    q = await session.execute(
        select(UserTerm).where(UserTerm.user_tg_id == user_tg_id, UserTerm.term == term)
    )
    row = q.scalar_one_or_none()
    if row:
        row.category = category
        return
    session.add(UserTerm(user_tg_id=user_tg_id, term=term, category=category))
