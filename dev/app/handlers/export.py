# -*- coding: utf-8 -*-
from __future__ import annotations
from datetime import datetime
import tempfile
from aiogram import Router, F, types
from aiogram.filters import Command

from app.core.db import session_scope
from app.repo.users import get_or_create_user
from app.repo.records import get_operations_range
from app.services.periods import parse_free_period, period_preset, fmt_date, label_for_period
from app.services.export_xlsx import build_xlsx
from app.services.export_pdf import try_build_pdf

router = Router(name=__name__)

async def _export_xlsx(m: types.Message, d1, d2, label: str):
    async with session_scope() as s:
        user = await get_or_create_user(s, m.from_user.id, m.from_user.username)
        ops = await get_operations_range(s, user.id, d1, d2)
    if not ops:
        await m.answer("Нет данных за выбранный период."); return
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        path = tmp.name
    build_xlsx(ops, d1, d2, path, title=f"Отчёт за {label}")
    await m.answer_document(types.FSInputFile(path), caption=f"📊 Экспорт (XLSX) — {label}")

async def _export_pdf(m: types.Message, d1, d2, label: str):
    async with session_scope() as s:
        user = await get_or_create_user(s, m.from_user.id, m.from_user.username)
        ops = await get_operations_range(s, user.id, d1, d2)
    if not ops:
        await m.answer("Нет данных за выбранный период."); return
    ok, path_or_msg = try_build_pdf(ops, d1, d2, title=f"Отчёт за {label}")
    if ok:
        await m.answer_document(types.FSInputFile(path_or_msg), caption=f"📄 Экспорт (PDF) — {label}")
    else:
        await m.answer(f"PDF сейчас недоступен: {path_or_msg}\nИспользуй /export_xlsx.")

@router.message(Command("export"))
async def cmd_export_default(m: types.Message):
    d1,d2 = period_preset("month")
    await _export_xlsx(m, d1, d2, "месяц")

@router.message(Command("export_xlsx"))
async def cmd_export_xlsx(m: types.Message):
    d1,d2 = period_preset("month")
    await _export_xlsx(m, d1, d2, "месяц")

@router.message(Command("export_pdf"))
async def cmd_export_pdf(m: types.Message):
    d1,d2 = period_preset("month")
    await _export_pdf(m, d1, d2, "месяц")

@router.message(F.text.func(lambda t: t and not t.startswith("/") and "экспорт" in t.lower()))
async def nl_export(m: types.Message):
    s = (m.text or "").lower()
    parsed = parse_free_period(s)
    d1,d2,label = period_preset("month")[0], period_preset("month")[1], "месяц"
    if parsed: d1,d2,label = parsed
    if "pdf" in s or "пдф" in s:
        await _export_pdf(m, d1, d2, label)
    else:
        await _export_xlsx(m, d1, d2, label)
