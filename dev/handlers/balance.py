# app/handlers/balance.py
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.core.db import session_scope
from app.repo.users import get_or_create_user
from app.repo.records import balance as repo_balance

router = Router(name=__name__)

@router.message(Command("balance"))
async def cmd_balance(m: Message) -> None:
    async with session_scope() as s:
        user = await get_or_create_user(s, m.from_user.id, m.from_user.username)
        bal = await repo_balance(s, user.id)
    sign = "" if bal == 0 else ("+" if bal > 0 else "-")
    await m.answer(f"💼 Баланс: <b>{sign}{abs(bal):.2f} BYN</b>", parse_mode="HTML")
