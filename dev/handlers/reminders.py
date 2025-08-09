# app/handlers/reminders.py
from __future__ import annotations

from datetime import datetime, date
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.core.config import settings
from app.core.db import session_scope
from app.repo.users import get_or_create_user
from app.repo.reminders import create_reminder, list_upcoming_for_day
from app.services.reminders import parse_remind_args

router = Router(name=__name__)

@router.message(Command("remind"))
async def cmd_remind(m: Message) -> None:
    """
    /remind <YYYY-MM-DD HH:MM Текст>
    /remind завтра HH:MM Текст
    /remind через N мин|час Текст
    """
    arg = (m.text or "").partition(" ")[2]
    try:
        when_utc, text = parse_remind_args(arg)
    except ValueError as e:
        await m.answer(f"Формат: /remind YYYY-MM-DD HH:MM <текст>\nТакже: «завтра HH:MM <текст>», «через N мин|час <текст>».\n\nОшибка: {e}")
        return

    async with session_scope() as s:
        user = await get_or_create_user(s, m.from_user.id, m.from_user.username)
        r = await create_reminder(s, user.id, text, when_utc)

    # отвечаем в локальной TZ
    local_dt = when_utc.astimezone(ZoneInfo(settings.tz)).strftime("%Y-%m-%d %H:%M")
    await m.answer(f"⏰ Ок, напомню <b>{local_dt}</b>: {text}", parse_mode="HTML")

@router.message(Command("reminders"))
async def cmd_reminders_list(m: Message) -> None:
    tz = ZoneInfo(settings.tz)
    today = datetime.now(tz).date()

    async with session_scope() as s:
        user = await get_or_create_user(s, m.from_user.id, m.from_user.username)
        items = await list_upcoming_for_day(s, user.id, today)

    if not items:
        await m.answer("Сегодня напоминаний нет.")
        return

    lines = ["🗓 <b>Напоминания на сегодня:</b>", ""]
    for i, r in enumerate(items, 1):
        local_dt = r.when_at.astimezone(tz).strftime("%H:%M")
        lines.append(f"{i}. {local_dt} — {r.text}")
    await m.answer("\n".join(lines), parse_mode="HTML")
