# app/handlers/admin.py
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
import html

from app.core.config import settings
from app.core.db import session_scope
from app.repo.users import total_users, total_operations
from app.handlers import LOADED_HANDLERS, FAILED_HANDLERS

router = Router(name=__name__)

def _is_owner(user_id: int) -> bool:
    return user_id in (settings.owner_ids or [])

@router.message(Command("admin_stats"))
async def cmd_admin_stats(m: Message) -> None:
    if not _is_owner(m.from_user.id):
        return
    async with session_scope() as s:
        u = await total_users(s)
        o = await total_operations(s)
    await m.answer(f"📊 users: {u}\n🧾 operations: {o}")

@router.message(Command("admin_broadcast"))
async def cmd_admin_broadcast(m: Message) -> None:
    if not _is_owner(m.from_user.id):
        return
    text = (m.text or "").partition(" ")[2].strip()
    if not text:
        await m.answer("Формат: /admin_broadcast <сообщение>")
        return
    await m.answer("Броадкаст (демо): отправка только инициатору.\n\n" + text)

@router.message(Command("admin_handlers"))
async def cmd_admin_handlers(m: Message) -> None:
    if not _is_owner(m.from_user.id):
        return
    lines = ["<b>Handlers</b>"]
    if LOADED_HANDLERS:
        lines.append("✅ loaded: " + ", ".join(LOADED_HANDLERS))
    if FAILED_HANDLERS:
        lines.append("\n❌ failed:")
        for k, v in FAILED_HANDLERS.items():
            lines.append(f"— <b>{k}</b>:\n<code>{html.escape(v)}</code>\n")
    await m.answer("\n".join(lines), parse_mode="HTML")
