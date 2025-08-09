# -*- coding: utf-8 -*-
from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo
import random

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from app.core.config import settings
from app.core.db import session_scope
from app.repo.users import get_or_create_user
from app.repo.records import add_operation, get_operations_range, delete_operation
from app.services.parser import parse_message
from app.services.periods import parse_free_period   # <-- чтобы не перехватывать отчёты
from app.services.learning import get_learned_category, save_user_term
from app.ui.ui import kb_pick_category, clean_name, extract_term

router = Router(name=__name__)

PENDING: dict[int, dict] = {}

CONFIRM_SAVE_VARIANTS = [
    "✅ Записал: «{term}» ({cat}) — {sign}{amt:.2f} BYN",
    "✅ Готово: «{term}» ({cat}) — {sign}{amt:.2f} BYN",
    "✅ Сохранил: «{term}» ({cat}) — {sign}{amt:.2f} BYN",
]
def pick(arr): return random.choice(arr)

def _today_dates():
    tz = ZoneInfo(settings.tz)
    now = datetime.now(tz)
    d = now.date()
    return d, d

@router.message(Command("records"))
async def cmd_records(m: Message) -> None:
    async with session_scope() as s:
        user = await get_or_create_user(s, m.from_user.id, m.from_user.username)
        start, end = _today_dates()
        ops = await get_operations_range(s, user.id, start, end)

    if not ops:
        await m.answer("🧾 За сегодня записей нет.", parse_mode="HTML")
        return

    lines = ["🧾 <b>Записи за сегодня:</b>", ""]
    btn_labels: list[tuple[str, int]] = []
    total_exp = total_inc = 0.0
    for i, o in enumerate(ops, 1):
        val = abs(float(o.amount))
        sign = "-" if o.type == "expense" else "+"
        if o.type == "expense": total_exp += val
        else: total_inc += val
        name = clean_name(o.description or o.category or "запись", o.category or "запись")
        lines.append(f"{i}. {name} — {sign}{val:.2f} BYN")
        btn_labels.append((f"{name} {sign}{val:.2f}", o.id))

    lines.append("")
    lines.append(f"💵 <b>Итого расходов:</b> -{total_exp:.2f} BYN")
    if total_inc > 0:
        lines.append(f"💵 <b>Итого доходов:</b> +{total_inc:.2f} BYN")

    rows, row = [], []
    for label, op_id in btn_labels:
        row.append(InlineKeyboardButton(text=f"🗑 {label}", callback_data=f"del:{op_id}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text="Закрыть", callback_data="del:cancel")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    await m.answer("\n".join(lines), parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("del:"))
async def cb_delete(c: CallbackQuery) -> None:
    data = c.data.split(":", 1)[1]
    if data == "cancel":
        await c.message.edit_reply_markup(reply_markup=None)
        await c.answer()
        return
    op_id = int(data)
    async with session_scope() as s:
        user = await get_or_create_user(s, c.from_user.id, c.from_user.username)
        ok = await delete_operation(s, user.id, op_id)
    await c.answer("Удалено" if ok else "Не нашёл запись.")
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

@router.callback_query(F.data.startswith("pickcat:"))
async def cb_pick_category(c: CallbackQuery) -> None:
    uid = c.from_user.id
    pend = PENDING.get(uid)
    if not pend:
        await c.answer("Нет ожидающей записи.")
        return
    choice = c.data.split(":", 1)[1]
    if choice == "__new__":
        pend["await_new"] = True
        await c.message.edit_text("Введи название новой категории одним сообщением или нажми «Отмена».")
        await c.answer()
        return
    await finalize_add(c, chosen_category=choice, learned_now=True)

@router.callback_query(F.data == "cancel")
async def cb_cancel(c: CallbackQuery) -> None:
    PENDING.pop(c.from_user.id, None)
    await c.message.edit_reply_markup(reply_markup=None)
    await c.answer()

@router.message(F.text.func(lambda t: bool(t)))
async def free_text(m: Message) -> None:
    uid = m.from_user.id

    # 0) Если это фраза про отчёты — НЕ трогаем, пусть обработает handlers.reports
    if parse_free_period(m.text or ""):
        return

    # 1) Этап ввода новой категории
    pend = PENDING.get(uid)
    if pend and pend.get("await_new"):
        custom = (m.text or "").strip()
        if not custom:
            await m.answer("Пусто. Введи название категории или нажми «Отмена».")
            return
        await finalize_add(m, chosen_category=custom, learned_now=True)
        return

    raw = (m.text or "").strip()
    if not raw:
        return

    # 2) Мультистрочный ввод: каждая строка отдельно
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    confirmations: list[str] = []
    asked = False

    async with session_scope() as s:
        user = await get_or_create_user(s, uid, m.from_user.username)

        for line in lines:
            parsed = parse_message(line, user_tg_id=uid)
            if not parsed:
                continue

            term = extract_term(parsed["raw"]) or (parsed["product"] or "").capitalize() or "Позиция"

            learned = get_learned_category(uid, term)
            if learned and (not parsed["category"] or parsed["category"] in ("Прочее", "Прочие платежи")):
                parsed["category"] = learned

            if (not parsed["category"] or parsed["category"] in ("Прочее", "Прочие платежи")) and not asked:
                PENDING[uid] = {"amount": parsed["amount"], "type": parsed["type"], "term": term, "raw": parsed["raw"]}
                await m.answer(
                    f"Я пока не выучил слово «{term}». К какой категории это относится?\n"
                    f"Выбери из списка или добавь свою.",
                    reply_markup=kb_pick_category()
                )
                asked = True
                continue

            await add_operation(
                session=s,
                user_id=user.id,
                amount=parsed["amount"],
                category=parsed["category"],
                description=parsed["raw"],  # ВАЖНО: только текущая строка
                op_type=parsed["type"],
            )
            sign = "+" if parsed["type"] == "income" else "-"
            confirmations.append(
                pick(CONFIRM_SAVE_VARIANTS).format(
                    term=term, cat=parsed["category"], sign=sign, amt=parsed["amount"]
                )
            )

    if confirmations:
        await m.answer("\n".join(confirmations), parse_mode="HTML")

async def finalize_add(obj: Message | CallbackQuery, chosen_category: str,
                       learned_now: bool = False) -> None:
    uid = obj.from_user.id
    pend = PENDING.pop(uid, None)
    if not pend:
        if isinstance(obj, CallbackQuery):
            await obj.answer("Нет ожидающей записи.")
        else:
            await obj.answer("Нет ожидающей записи.")
        return

    amount, op_type, term, raw = pend["amount"], pend["type"], pend["term"], pend["raw"]

    async with session_scope() as s:
        user = await get_or_create_user(s, uid, getattr(obj.from_user, "username", None))
        await add_operation(
            session=s,
            user_id=user.id,
            amount=amount,
            category=chosen_category,
            description=raw,
            op_type=op_type,
        )
        if learned_now:
            save_user_term(uid, term, chosen_category)

    sign = "+" if op_type == "income" else "-"
    text = random.choice(CONFIRM_SAVE_VARIANTS).format(
        term=term, cat=chosen_category, sign=sign, amt=amount
    )
    if isinstance(obj, CallbackQuery):
        await obj.message.edit_text(text, parse_mode="HTML")
        await obj.answer("Готово")
    else:
        await obj.answer(text, parse_mode="HTML")
