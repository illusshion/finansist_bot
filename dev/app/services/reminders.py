# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.repo.reminders import due_reminders, mark_done


def _ensure_naive_utc(dt: datetime) -> datetime:
    """
    Всегда работаем с naive UTC (tzinfo=None), потому что в БД колонка
    TIMESTAMP WITHOUT TIME ZONE. Это убирает конфликт aware/naive.
    """
    if dt.tzinfo is not None:
        # Переводим в UTC и убираем tzinfo
        return dt.astimezone(tz=None).replace(tzinfo=None, microsecond=0)
    return dt.replace(microsecond=0)


async def fire_due_reminders(session: AsyncSession, now: datetime) -> int:
    """
    Находит все напоминания, время которых <= now, помечает выполненными.
    (Отправку сообщений в Telegram можно добавить позже: сюда легко
    прокинуть bot и tg_id пользователя.)

    Возвращает количество обработанных напоминаний.
    """
    now = _ensure_naive_utc(now)

    rows = await due_reminders(session, now)  # type: Sequence
    processed = 0

    for r in rows:
        # Здесь можно отправить сообщение пользователю через bot, если нужно:
        # if bot is not None:
        #     await bot.send_message(chat_id=<tg_id>, text=f"🔔 Напоминание: {r.text}")
        await mark_done(session, r.id)
        processed += 1

    return processed
