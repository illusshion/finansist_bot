# -*- coding: utf-8 -*-
from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo
import random
import logging

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from app.core.config import settings
from app.core.db import session_scope
from app.repo.users import get_or_create_user
from app.repo.records import add_operation, get_operations_range, delete_operation
from app.services.parser import parse_message
from app.services.periods import parse_free_period   # не перехватываем отчёты
from app.services.learning import get_learned_category, save_user_term
from app.ui.ui import kb_pick_category, clean_name, extract_term

log = logging.getLogger(__name__)
router = Router(name=__name__)

# Очередь обучения терминов:
# PENDING[user_id] = {
#   "queue": [ {"amount": float, "type": "income|expense", "term": str, "raw": str}, ... ],
#   "msg_id": int | None,     # id сообщения с инлайн-клавиатурой
#   "await_new": False        # ждём ввод кастомной категории
# }
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
    for o in ops:
        sign = "-" if o.type == "expense" else "+"
        if o.type == "expense":
            total_exp += float(abs(o.amount))
        else:
            total_inc += float(abs(o.amount))
        lines.append(f"{clean_name(o.description or o.category)} — {sign}{abs(float(o.amount)):.2f} BYN")
        btn_labels.append((f"🗑 {clean_name(o.description or o.category)}", o.id))

    if total_exp > 0 or total_inc > 0:
        lines.append("")
    if total_exp > 0:
        lines.append(f"💵 <b>Итого расходов:</b> -{total_exp:.2f} BYN")
    if total_inc > 0:
        lines.append(f"💵 <b>Итого доходов:</b> +{total_inc:.2f} BYN")

    from app.ui.keyboards import deletion_keyboard
    await m.answer("\n".join(lines), parse_mode="HTML",
                   reply_markup=deletion_keyboard(btn_labels) if btn_labels else None)

# === Сохранение по свободному тексту (включая многострочник) ===

@router.message(F.text.func(lambda t: bool(t)))
async def free_text(m: Message) -> None:
    uid = m.from_user.id

    # 0) Если это фраза про отчёты — НЕ трогаем, пусть обработает handlers.reports
    if parse_free_period(m.text or ""):
        return

    # 1) Этап ввода новой категории в процессе обучения
    pend = PENDING.get(uid)
    if pend and pend.get("await_new"):
        custom = (m.text or "").strip()
        if not custom:
            await m.answer("Пусто. Введи название категории или нажми «Отмена».")
            return
        await _finalize_current_and_continue(m, chosen_category=custom, learned_now=True)
        return

    text = (m.text or "").strip()
    if not text:
        return

    lines = [s for s in (t.strip() for t in text.splitlines()) if s]

    to_learn_queue: list[dict] = []
    saved: list[str] = []

    async with session_scope() as s:
        user = await get_or_create_user(s, uid, m.from_user.username)

        for line in lines:
            parsed = parse_message(line, user_tg_id=uid)
            if not parsed:
                continue

            term = extract_term(parsed["raw"]) or (parsed["product"] or "").capitalize() or "Позиция"

            # выученная категория — приоритетнее «Прочее»
            learned = get_learned_category(uid, term)
            if learned and (not parsed["category"] or parsed["category"] in ("Прочее", "Прочие платежи")):
                parsed["category"] = learned

            # неизвестные копим в очередь
            if (not parsed["category"]) or (parsed["category"] in ("Прочее", "Прочие платежи")):
                to_learn_queue.append({
                    "amount": parsed["amount"],
                    "type": parsed["type"],
                    "term": term,
                    "raw": parsed["raw"],
                })
                continue

            # известные — сохраняем сразу
            await add_operation(
                session=s,
                user_id=user.id,
                amount=parsed["amount"],
                category=parsed["category"],
                description=parsed["raw"],  # только текущая строка
                op_type=parsed["type"],
            )
            sign = "+" if parsed["type"] == "income" else "-"
            saved.append(f"«{term}» ({parsed['category']}) — {sign}{parsed['amount']:.2f} BYN")

    # 2) Сначала сообщаем про сохранённые записи (UX — сверху)
    if saved:
        msg = ["✅ Сохранил записей: <b>{}</b>.".format(len(saved))]
        for sline in saved[:10]:
            msg.append("• " + sline)
        if len(saved) > 10:
            msg.append(f"… и ещё {len(saved) - 10}")
        await m.answer("\n".join(msg), parse_mode="HTML")

    # 3) Если есть что обучать — запускаем мастер
    if to_learn_queue:
        PENDING[uid] = {"queue": to_learn_queue, "msg_id": None, "await_new": False}
        await _ask_next_term(m)
        return

    # 4) Иначе — ничего обучать, всё ок
    if not saved:
        await m.answer("Ничего не понял. Напиши, например: «еда 10» или несколько строк с суммами.")

async def _ask_next_term(m: Message | CallbackQuery) -> None:
    uid = m.from_user.id
    pend = PENDING.get(uid)
    if not pend or not pend.get("queue"):
        # Очередь пуста
        text = "Готово. Все операции сохранены."
        if isinstance(m, CallbackQuery):
            try:
                await m.message.edit_text(text, parse_mode="HTML", reply_markup=None)
            finally:
                await _safe_answer(m)
        else:
            await m.answer(text, parse_mode="HTML")
        PENDING.pop(uid, None)
        return

    current = pend["queue"][0]
    text = (
        "Я не выучил слово «{term}». К какой категории это относится?\n"
        "Выбери из списка или добавь свою."
    ).format(term=current["term"])
    kb = kb_pick_category()  # клавиатура: pickcat:<cat>, pickcat:__new__, cancel

    if isinstance(m, CallbackQuery):
        try:
            await m.message.edit_text(text, reply_markup=kb)
            pend["msg_id"] = m.message.message_id
        finally:
            await _safe_answer(m)
    else:
        msg = await m.answer(text, reply_markup=kb)
        pend["msg_id"] = msg.message_id

async def _finalize_current_and_continue(obj: Message | CallbackQuery, *, chosen_category: str, learned_now: bool) -> None:
    uid = obj.from_user.id
    pend = PENDING.get(uid)
    if not pend or not pend.get("queue"):
        if isinstance(obj, CallbackQuery):
            await _safe_answer(obj, "Нет ожидающей записи.")
        else:
            await obj.answer("Нет ожидающей записи.")
        return

    current = pend["queue"].pop(0)
    amount, op_type, term, raw = current["amount"], current["type"], current["term"], current["raw"]

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
    text = pick(CONFIRM_SAVE_VARIANTS).format(term=term, cat=chosen_category, sign=sign, amt=amount)

    if isinstance(obj, CallbackQuery):
        try:
            await obj.message.edit_text(text, parse_mode="HTML")
        finally:
            await _safe_answer(obj, "Готово")
        # Следующий вопрос в том же месте
        await _ask_next_term(obj)
    else:
        await obj.answer(text, parse_mode="HTML")
        await _ask_next_term(obj)

# ==== Callbacks ====

async def _safe_answer(c: CallbackQuery, text: str | None = None):
    try:
        await c.answer(text or "")
    except Exception as e:
        log.debug("callback answer suppressed: %s", e)

# Кнопка «Отмена»
@router.callback_query(F.data == "cancel")
async def cb_cancel(c: CallbackQuery):
    PENDING.pop(c.from_user.id, None)
    try:
        await c.message.edit_text("Отменено. Ничего не обучал для оставшихся строк.", reply_markup=None)
    finally:
        await _safe_answer(c, "OK")

# Кнопка «Добавить свою…» (pickcat:__new__)
@router.callback_query(F.data == "pickcat:__new__")
async def cb_add_custom(c: CallbackQuery):
    uid = c.from_user.id
    pend = PENDING.setdefault(uid, {})
    pend["await_new"] = True
    try:
        await c.message.edit_text("Введи название категории для текущего слова. Потом продолжим.")
    finally:
        await _safe_answer(c)

# Выбор готовой категории: pickcat:<имя>
@router.callback_query(F.data.startswith("pickcat:"))
async def cb_pick_category(c: CallbackQuery):
    data = (c.data or "")
    if data in ("pickcat:__new__",):
        # это обработает cb_add_custom
        await _safe_answer(c)
        return

    chosen = data[len("pickcat:"):]
    if not chosen:
        await _safe_answer(c, "Ошибка категории")
        return

    await _finalize_current_and_continue(c, chosen_category=chosen, learned_now=True)

# Удаление записи (кнопки из /records)
@router.callback_query(F.data.startswith("del:"))
async def cb_delete(c: CallbackQuery):
    try:
        rec_id = int((c.data or "")[4:])
    except Exception:
        await _safe_answer(c, "Ошибка id")
        return

    async with session_scope() as s:
        await delete_operation(s, rec_id)

    try:
        await c.message.edit_text("Удалено.", reply_markup=None)
    finally:
        await _safe_answer(c, "OK")
