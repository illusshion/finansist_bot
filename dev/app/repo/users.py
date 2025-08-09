# app/repo/users.py
from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.operation import Operation

async def get_or_create_user(session: AsyncSession, tg_id: int, username: str | None = None) -> User:
    q = await session.execute(select(User).where(User.telegram_id == tg_id))
    user = q.scalar_one_or_none()
    if user:
        if username and user.username != username:
            user.username = username
        return user
    user = User(telegram_id=tg_id, username=username)
    session.add(user)
    await session.flush()
    return user

async def set_language(session: AsyncSession, user_db_id: int, lang: str) -> None:
    q = await session.execute(select(User).where(User.id == user_db_id))
    u = q.scalar_one_or_none()
    if u:
        u.language = lang[:10].lower()
        await session.flush()

async def set_currency(session: AsyncSession, user_db_id: int, currency: str) -> None:
    q = await session.execute(select(User).where(User.id == user_db_id))
    u = q.scalar_one_or_none()
    if u:
        u.currency = currency[:10].upper()
        await session.flush()

async def set_daily_limit(session: AsyncSession, user_db_id: int, amount: float | None) -> None:
    q = await session.execute(select(User).where(User.id == user_db_id))
    u = q.scalar_one_or_none()
    if u:
        u.daily_limit = amount
        await session.flush()

# Админская статистика
async def total_users(session: AsyncSession) -> int:
    q = await session.execute(select(func.count(User.id)))
    return int(q.scalar_one() or 0)

async def total_operations(session: AsyncSession) -> int:
    q = await session.execute(select(func.count(Operation.id)))
    return int(q.scalar_one() or 0)
