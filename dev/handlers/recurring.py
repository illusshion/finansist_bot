# app/handlers/recurring.py
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
import re

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.core.config import settings
from app.core.db import session_scope
from app.repo.users import get_or_create_user
from app.repo.recurring_ops import create_recurring, list_all_for_user, delete_recurring
from app.services.recurring import _next_after  # используем расчёт next_run

router = Router(name=__name__)

_HELP = (
    "Повторяющиеся операции:\n"
    "/recurring_add daily HH:MM <+|-><сумма> <Категория> [описание]\n"
    "/recurring_add weekly <0-6> HH:MM <+|-><сумма> <Категория> [описание]\n"
    "/recurring_add monthly <1-28> HH:MM <+|-><сумма> <Категория> [описание]\n\n"
    "Пояснения:\n"
    "  • Понедельник=0 … воскресенье=6\n"
    "  • Знак суммы определяет тип: + доход, - расход\n"
    "Примеры:\n"
    "  /recurring_add daily 09:00 -5 Сигареты\n"
    "  /recurring_add weekly 5 20:30 -50 Развлечения Пятничный бар\n"
    "  /recurring_add monthly 1 10:00 +200 Доход Партнёрка\n\n"
    "/recurring_list — список правил\n"
    "/recurring_del <id> — удаление правила"
)

@router.message(Command("recurring_help"))
async def cmd_recurring_help(m: Message) -> None:
    await m.answer(_HELP)

@router.message(Command("recurring_add"))
async def cmd_recurring_add(m: Message) -> None:
    """
    Форматы:
      daily HH:MM +/-SUM Category [desc...]
      weekly DOW HH:MM +/-SUM Category [desc...]
      monthly DOM HH:MM +/-SUM Category [desc...]
    """
    args = (m.text or "").split(maxsplit=2)
    if len(args) < 3:
        await m.answer(_HELP)
        return
    _, _, tail = args
    parts = tail.split()
    if len(parts) < 4:
        await m.answer(_HELP)
        return

    period = parts[0].lower()
    if period not in ("daily", "weekly", "monthly"):
        await m.answer(_HELP); return

    idx = 1
    dow = dom = None

    if period == "daily":
        pass
    elif period == "weekly":
        if len(parts) < 5:
            await m.answer(_HELP); return
        try:
            dow = int(parts[1])
            if dow < 0 or dow > 6: raise ValueError
        except Exception:
            await m.answer("DOW должен быть числом 0..6"); return
        idx += 1
    elif period == "monthly":
        if len(parts) < 5:
            await m.answer(_HELP); return
        try:
            dom = int(parts[1])
            if dom < 1 or dom > 28: raise ValueError
        except Exception:
            await m.answer("День месяца 1..28"); return
        idx += 1

    hm = parts[idx]; idx += 1
    if not re.match(r"^\d{2}:\d{2}$", hm):
        await m.answer("Время в формате HH:MM"); return
    hour, minute = map(int, hm.split(":"))

    sum_token = parts[idx]; idx += 1
    if not re.match(r"^[\+\-]\d+(\.\d{1,2})?$", sum_token):
        await m.answer("Сумма с знаком: +100 или -5.50"); return
    amount = float(sum_token[1:])
    op_type = "income" if sum_token.startswith("+") else "expense"

    category = parts[idx]; idx += 1
    desc = " ".join(parts[idx:]) if idx < len(parts) else None

    tz = ZoneInfo(settings.tz)
    local_now = datetime.now(tz)
    next_run = _next_after(period, local_now, hour, minute, dow, dom)

    async with session_scope() as s:
        user = await get_or_create_user(s, m.from_user.id, m.from_user.username)
        r = await create_recurring(
            s, user.id, amount, category, desc, op_type,
            period, hour, minute, dow, dom, next_run
        )

    lr = next_run.astimezone(tz).strftime("%Y-%m-%d %H:%M")
    await m.answer(f"♻️ Добавлено правило #{r.id}: {period} {hm} {sum_token} {category}"
                   f"{(' ' + desc) if desc else ''}\nБлижайший запуск: {lr}")

@router.message(Command("recurring_list"))
async def cmd_recurring_list(m: Message) -> None:
    tz = ZoneInfo(settings.tz)
    async with session_scope() as s:
        user = await get_or_create_user(s, m.from_user.id, m.from_user.username)
        recs = await list_all_for_user(s, user.id)

    if not recs:
        await m.answer("Правил нет. См. /recurring_help")
        return

    lines = ["♻️ <b>Рекуррентные операции</b>", ""]
    for r in recs:
        sched = f"{r.period} "
        if r.period == "weekly":
            sched += f"dow={r.dow} "
        if r.period == "monthly":
            sched += f"dom={r.dom} "
        sched += f"{r.hour:02d}:{r.minute:02d}"
        sign = "+" if r.op_type == "income" else "-"
        nxt = r.next_run.astimezone(tz).strftime("%Y-%m-%d %H:%M")
        lines.append(f"#{r.id}: {sched} | {sign}{r.amount:.2f} {r.category} | next: {nxt} | {r.description or ''}")
    await m.answer("\n".join(lines), parse_mode="HTML")

@router.message(Command("recurring_del"))
async def cmd_recurring_del(m: Message) -> None:
    parts = (m.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await m.answer("Формат: /recurring_del <id>")
        return
    rec_id = int(parts[1])
    async with session_scope() as s:
        user = await get_or_create_user(s, m.from_user.id, m.from_user.username)
        ok = await delete_recurring(s, rec_id, user.id)
    await m.answer("Удалено." if ok else "Не нашёл правило.")
