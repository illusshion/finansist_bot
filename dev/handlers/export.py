# app/handlers/export.py
from __future__ import annotations

import re
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile

from app.core.db import session_scope
from app.repo.users import get_or_create_user
from app.repo.records import get_operations_range
from app.services.date_period import period_from_text
from app.services.export_xlsx import build_xlsx
from app.services.export_pdf import build_pdf

router = Router(name=__name__)

_RX_EXPORT = re.compile(r"\bэкспорт\b", re.IGNORECASE)
_RX_PDF = re.compile(r"\b(pdf|пдф)\b", re.IGNORECASE)
_RX_XLSX = re.compile(r"\b(xlsx|excel|эксель|иксэл|иксель)\b", re.IGNORECASE)

async def _export_and_send(m: Message, kind: str, arg_text: str) -> None:
    start, end, label = period_from_text(arg_text)
    async with session_scope() as s:
        user = await get_or_create_user(s, m.from_user.id, m.from_user.username)
        ops = await get_operations_range(s, user.id, start, end)

    if not ops:
        await m.answer(f"{kind.upper()} {label}: записей нет.", parse_mode="HTML")
        return

    username = m.from_user.username or str(m.from_user.id)
    if kind == "xlsx":
        path = build_xlsx(ops, start, end, user_label=username)
        await m.answer_document(FSInputFile(path), caption=f"Экспорт {label} (XLSX).")
    else:
        path = build_pdf(ops, start, end, user_label=username)
        await m.answer_document(FSInputFile(path), caption=f"Экспорт {label} (PDF).")

@router.message(Command("export"))
async def cmd_export_xlsx(m: Message) -> None:
    arg = (m.text or "").partition(" ")[2]
    await _export_and_send(m, "xlsx", arg)

@router.message(Command("export_pdf"))
async def cmd_export_pdf(m: Message) -> None:
    arg = (m.text or "").partition(" ")[2]
    await _export_and_send(m, "pdf", arg)

@router.message(F.text.func(lambda t: t and _RX_EXPORT.search(t)))
async def msg_export_nl(m: Message) -> None:
    text = m.text or ""
    kind = "pdf" if _RX_PDF.search(text) else ("xlsx" if _RX_XLSX.search(text) else "pdf")
    await _export_and_send(m, kind, text)
