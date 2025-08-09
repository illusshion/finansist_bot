# app/handlers/records_bulk.py
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from app.core.db import session_scope
from app.repo.users import get_or_create_user
from app.repo.records import add_operation
from app.services.parser import parse_message
from app.services.learning import save_user_term

router = Router(name=__name__)

_BULK_STATE: dict[int, list[str]] = {}  # tg_id -> lines

@router.message(Command("bulk_start"))
async def cmd_bulk_start(m: Message) -> None:
    _BULK_STATE[m.from_user.id] = []
    await m.answer(
        "Режим многострочного ввода.\nВставляй строки по одной или целым блоком. Когда закончишь — /bulk_end.\nОтмена — /cancel."
    )

@router.message(Command("bulk_end"))
async def cmd_bulk_end(m: Message) -> None:
    lines = _BULK_STATE.pop(m.from_user.id, None)
    if not lines:
        await m.answer("Нет данных. Используй /bulk_start.")
        return

    added = 0
    unknown: list[tuple[str, str]] = []  # (raw/product, suggested_cat)

    async with session_scope() as s:
        user = await get_or_create_user(s, m.from_user.id, m.from_user.username)
        for raw in lines:
            parsed = parse_message(raw, user_tg_id=m.from_user.id)
            if not parsed:
                continue
            await add_operation(
                session=s, user_id=user.id,
                amount=parsed["amount"], category=parsed["category"],
                description=parsed["product"], op_type=parsed["type"],
            )
            added += 1
            if parsed["category"] == "Прочее":
                unknown.append((parsed["product"] or parsed["raw"], "Еда"))

    msg = [f"Готово. Добавлено записей: <b>{added}</b>."]
    if unknown:
        msg.append("")
        msg.append("⚠️ Необученные термины:")
        for term, sug in unknown[:10]:
            msg.append(f"• {term} → (например: {sug})")
        msg.append("")
        msg.append("Чтобы обучить быстро: отправь строку вида\n<code>обучи: термин = Категория</code>\nпо одной на строку.")

    await m.answer("\n".join(msg), parse_mode="HTML")

@router.message(F.text.func(lambda t: t and t.lower().startswith("обучи:")))
async def bulk_teach_line(m: Message) -> None:
    # формат: обучи: термин = Категория
    tail = (m.text or "")[6:].strip(": ").strip()
    if "=" not in tail:
        await m.answer("Формат: <code>обучи: термин = Категория</code>", parse_mode="HTML")
        return
    term, cat = [x.strip() for x in tail.split("=", 1)]
    if not term or not cat:
        await m.answer("Формат: <code>обучи: термин = Категория</code>", parse_mode="HTML")
        return
    save_user_term(m.from_user.id, term, cat, global_scope=False)
    await m.answer(f"Выучил: «{term}» → {cat}")

@router.message(F.text & ~F.text.startswith("/"))
async def bulk_collect(m: Message) -> None:
    if m.from_user.id not in _BULK_STATE:
        return  # не в bulk-режиме, пусть другие хендлеры отработают
    chunk = (m.text or "").strip()
    if not chunk:
        return
    # поддержка вставки блока
    for line in chunk.splitlines():
        line = line.strip()
        if line:
            _BULK_STATE[m.from_user.id].append(line)
    await m.answer(f"Принял. Строк в буфере: {len(_BULK_STATE[m.from_user.id])}. Заверши /bulk_end.")
