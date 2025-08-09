# app/handlers/settings.py
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.core.db import session_scope
from app.repo.users import get_or_create_user, set_language, set_currency, set_daily_limit

router = Router(name=__name__)

@router.message(Command("language"))
async def cmd_language(m: Message) -> None:
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) == 1:
        await m.answer("Язык: ru | en\nПример: /language ru")
        return
    lang = parts[1].strip().lower()
    if lang not in ("ru", "en"):
        await m.answer("Поддерживаем: ru, en")
        return
    async with session_scope() as s:
        user = await get_or_create_user(s, m.from_user.id, m.from_user.username)
        await set_language(s, user.id, lang)
    await m.answer(f"Ок, язык: {lang}")

@router.message(Command("currency"))
async def cmd_currency(m: Message) -> None:
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) == 1:
        await m.answer("Валюта: BYN | USD | EUR (пока влияет только на отображение в будущем)\nПример: /currency BYN")
        return
    cur = parts[1].strip().upper()[:10]
    async with session_scope() as s:
        user = await get_or_create_user(s, m.from_user.id, m.from_user.username)
        await set_currency(s, user.id, cur)
    await m.answer(f"Ок, валюта: {cur}")

@router.message(Command("limit"))
async def cmd_limit(m: Message) -> None:
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) == 1:
        await m.answer("Дневной лимит расходов. Пример: /limit 50  (или /limit off)")
        return
    arg = parts[1].strip().lower()
    value = None
    if arg not in ("off", "none", "нет", "0"):
        try:
            value = float(arg.replace(",", "."))
        except Exception:
            await m.answer("Число или 'off'")
            return
    async with session_scope() as s:
        user = await get_or_create_user(s, m.from_user.id, m.from_user.username)
        await set_daily_limit(s, user.id, value)
    await m.answer(f"Лимит установлен: {value if value is not None else 'выключен'}")
