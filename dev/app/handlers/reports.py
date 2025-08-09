# -*- coding: utf-8 -*-
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, date
from aiogram import Router, F, types
from aiogram.filters import Command

from app.core.db import session_scope
from app.repo.users import get_or_create_user
from app.repo.records import get_operations_range, delete_operation
from app.services.periods import fmt_date, period_preset, parse_free_period, label_for_period
from app.ui.ui import kb_summary, kb_details, clean_name

router = Router(name=__name__)

CATEGORY_TITLE = {
    "еда": "Еда и напитки","еда и напитки": "Еда и напитки",
    "алкоголь": "Алкоголь","транспорт": "Транспорт","связь и интернет": "Связь и интернет",
    "подписки": "Подписки","коммунальные платежи": "Коммунальные платежи","развлечения": "Развлечения",
    "домашние расходы": "Домашние расходы","здоровье": "Здоровье","одежда": "Одежда",
    "прочее": "Прочие платежи","прочие платежи": "Прочие платежи","доход": "Доход","зарплата": "Зарплата",
}

def _norm_cat(cat: str | None) -> str:
    key = (cat or "Прочие платежи").strip().lower()
    return CATEGORY_TITLE.get(key, cat or "Прочие платежи")

def _aggregate(ops):
    from collections import defaultdict
    exp, inc = defaultdict(float), defaultdict(float)
    for o in ops:
        c = _norm_cat(o.category); v = abs(float(o.amount))
        (inc if o.type=="income" else exp)[c] += v
    return dict(sorted(exp.items(), key=lambda x:-x[1])), dict(sorted(inc.items(), key=lambda x:-x[1]))

async def _send_summary(target: types.Message, user_id: int, username: str | None,
                        d1: date, d2: date, label_override: str | None, edit: bool):
    df, dt = fmt_date(d1), fmt_date(d2)
    label = label_for_period(d1, d2, label_override)
    async with session_scope() as s:
        user = await get_or_create_user(s, user_id, username)
        ops = await get_operations_range(s, user.id, d1, d2)
    exp, inc = _aggregate(ops)
    has_any = bool(exp) or bool(inc)
    lines = [f"📊 <b>Отчёт за {label}:</b>", ""]
    if exp:
        lines.append("💸 <b>Расходы по категориям:</b>")
        for cat,val in exp.items(): lines.append(f"• {cat} — -{val:.2f} BYN")
        lines.append("")
    else:
        lines.append("💸 <b>Расходы:</b>\n• нет записей\n")
    if inc:
        lines.append("💰 <b>Доходы:</b>")
        for cat,val in inc.items(): lines.append(f"• +{val:.2f} BYN — {cat}")
    else:
        lines.append("💰 Доходов нет")
    kb = kb_summary(df, dt, has_any)
    if has_any: lines.append("\nПоказать детальный список позиций?")
    text = "\n".join(lines)
    if edit:
        try: await target.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception: await target.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=kb)

def _build_details(ops):
    expg, incg = defaultdict(list), defaultdict(list)
    for o in ops:
        (_norm_cat(o.category))
        (incg if o.type=="income" else expg)[_norm_cat(o.category)].append(o)
    lines=[]; btns=[]; total_exp=total_inc=0.0
    for cat in sorted(expg.keys()):
        lines.append(f"<b>{cat}:</b>")
        for i,o in enumerate(expg[cat],1):
            v=abs(float(o.amount)); total_exp+=v; nm=clean_name(o.description or "", cat)
            lines.append(f"{i}. {nm} — -{v:.2f} BYN"); btns.append((f"{nm} -{v:.2f}", o.id))
        lines.append("")
    for cat in sorted(incg.keys()):
        lines.append(f"<b>{cat}:</b>")
        for i,o in enumerate(incg[cat],1):
            v=abs(float(o.amount)); total_inc+=v; nm=clean_name(o.description or "", cat)
            lines.append(f"{i}. {nm} — +{v:.2f} BYN"); btns.append((f"{nm} +{v:.2f}", o.id))
        lines.append("")
    return ("\n".join(lines).strip(), btns, total_exp, total_inc)

@router.message(Command("report"))
async def cmd_report(m: types.Message): d1,d2=period_preset("day"); await _send_summary(m,m.from_user.id,m.from_user.username,d1,d2,None,False)
@router.message(Command("day"))
async def cmd_day(m: types.Message): d1,d2=period_preset("day"); await _send_summary(m,m.from_user.id,m.from_user.username,d1,d2,None,False)
@router.message(Command("week"))
async def cmd_week(m: types.Message): d1,d2=period_preset("week"); await _send_summary(m,m.from_user.id,m.from_user.username,d1,d2,None,False)
@router.message(Command("month"))
async def cmd_month(m: types.Message): d1,d2=period_preset("month"); await _send_summary(m,m.from_user.id,m.from_user.username,d1,d2,None,False)
@router.message(Command("year"))
async def cmd_year(m: types.Message): d1,d2=period_preset("year"); await _send_summary(m,m.from_user.id,m.from_user.username,d1,d2,None,False)

@router.message(F.text.func(lambda t: bool(t) and not t.startswith("/") and any(
    k in t.lower() for k in ("покажи","дай","отчет","отчёт","статист","сводк","сколько потратил","за последние","с "," по ","за месяц","за неделю","за год")
)))
async def nl_report(m: types.Message):
    parsed = parse_free_period(m.text or "")
    if not parsed: return
    d1,d2,label = parsed
    await _send_summary(m, m.from_user.id, m.from_user.username, d1, d2, label, False)

@router.callback_query(F.data.startswith("details:"))
async def cb_details(c: types.CallbackQuery):
    _, df, dt = (c.data or "").split(":", 2)
    d1 = datetime.strptime(df,"%Y-%m-%d").date(); d2 = datetime.strptime(dt,"%Y-%m-%d").date()
    label = label_for_period(d1,d2,None)
    async with session_scope() as s:
        user = await get_or_create_user(s, c.from_user.id, None)
        ops = await get_operations_range(s, user.id, d1, d2)
    body, btns, total_exp, total_inc = _build_details(ops)
    lines=[f"📝 <b>Детальный отчёт</b> за {label}",""]
    if body: lines.append(body); lines.append("")
    lines.append(f"💵 <b>Итого расходов:</b> -{total_exp:.2f} BYN")
    if total_inc>0: lines.append(f"💵 <b>Итого доходов:</b> +{total_inc:.2f} BYN")
    await c.message.edit_text("\n".join(lines).strip(), parse_mode="HTML", reply_markup=kb_details(btns, df, dt) if btns else None)
    await c.answer()

@router.callback_query(F.data.startswith("del:"))
async def cb_delete(c: types.CallbackQuery):
    try: _,sid,df,dt=(c.data or "").split(":",3); op_id=int(sid)
    except Exception: await c.answer("Некорректные данные"); return
    d1 = datetime.strptime(df,"%Y-%m-%d").date(); d2 = datetime.strptime(dt,"%Y-%m-%d").date()
    async with session_scope() as s:
        user = await get_or_create_user(s, c.from_user.id, None)
        ok = await delete_operation(s, user.id, op_id)
        ops = await get_operations_range(s, user.id, d1, d2)
    body, btns, total_exp, total_inc = _build_details(ops)
    label = label_for_period(d1,d2,None)
    lines=[f"📝 <b>Детальный отчёт</b> за {label}",""]
    if body: lines.append(body); lines.append("")
    lines.append(f"💵 <b>Итого расходов:</b> -{total_exp:.2f} BYN")
    if total_inc>0: lines.append(f"💵 <b>Итого доходов:</b> +{total_inc:.2f} BYN")
    await c.message.edit_text("\n".join(lines).strip(), parse_mode="HTML", reply_markup=kb_details(btns, df, dt) if btns else None)
    await c.answer("Удалено" if ok else "Не нашёл запись")

@router.callback_query(F.data.startswith("close:"))
async def cb_close(c: types.CallbackQuery):
    _, df, dt = (c.data or "").split(":", 2)
    d1 = datetime.strptime(df,"%Y-%m-%d").date(); d2 = datetime.strptime(dt,"%Y-%m-%d").date()
    await _send_summary(c.message, c.from_user.id, c.from_user.username, d1, d2, None, True)
    await c.answer()
