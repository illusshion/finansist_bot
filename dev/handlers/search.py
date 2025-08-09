# app/handlers/search.py
# Свободный поиск вида «такси июль», «сигареты вчера», «еда неделя»

from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message

from app.core.db import session_scope
from app.repo.users import get_or_create_user
from app.services.date_period import period_from_text
from app.services.search import search_operations

router = Router(name=__name__)


def _fmt_ops(ops: list, title: str) -> str:
    if not ops:
        return f"🔎 <b>{title}</b>\nНичего не нашёл."
    lines = [f"🔎 <b>{title}</b>", ""]
    total_exp = total_inc = 0.0
    for i, o in enumerate(ops, 1):
        sign = "-" if o.type == "expense" else "+"
        val = abs(float(o.amount))
        name = (o.description or o.category or "запись").strip()
        lines.append(f"{i}. {name} — {sign}{val:.2f} BYN")
        if o.type == "expense": total_exp += val
        else: total_inc += val
    lines.append("")
    if total_exp: lines.append(f"💵 Итого расходов: -{total_exp:.2f} BYN")
    if total_inc: lines.append(f"💵 Итого доходов: +{total_inc:.2f} BYN")
    return "\n".join(lines)


@router.message(F.text.func(lambda t: t and not t.startswith("/") and any(k in t.lower() for k in ("вчера","недел","месяц","январ","феврал","март","апрел","май","июн","июл","август","сентябр","октябр","ноябр","декабр"))))
async def text_search_period(m: Message) -> None:
    text = m.text or ""
    start, end, label = period_from_text(text)

    # ключевая фраза = всё сообщение (мы не вырезаем период отдельно — достаточно)
    query = text
    async with session_scope() as s:
        user = await get_or_create_user(s, m.from_user.id, m.from_user.username)
        ops = await search_operations(s, user.id, query, start, end)

    await m.answer(_fmt_ops(ops, f"Поиск {label}"), parse_mode="HTML")
