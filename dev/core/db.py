# app/core/db.py
# Async SQLAlchemy + session factory + инициализация схемы

from __future__ import annotations

from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

# Один движок на приложение
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    future=True,
)

# Фабрика сессий
Session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@asynccontextmanager
async def session_scope() -> AsyncSession:
    """
    Контекст для работы с БД:
    >>> async with session_scope() as s:
    ...     await s.execute(...)
    """
    session: AsyncSession = Session()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

async def init_db() -> None:
    """
    Создание таблиц для старта без Alembic.
    Все модели используют общий Base из app.models.user.
    """
    from app.models.user import Base  # единый Base для User, Operation, Reminder, RecurringOp
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
