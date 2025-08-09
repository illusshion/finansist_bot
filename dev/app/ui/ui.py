# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def kb_summary(df: str, dt: str, has_any: bool) -> InlineKeyboardMarkup | None:
    if not has_any:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📋 Детали", callback_data=f"details:{df}:{dt}")]]
    )

def kb_details(ops_labels, df: str, dt: str) -> InlineKeyboardMarkup:
    rows, row = [], []
    for label, op_id in ops_labels:
        row.append(InlineKeyboardButton(text=f"🗑 {label}", callback_data=f"del:{op_id}:{df}:{dt}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text="Закрыть", callback_data=f"close:{df}:{dt}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_pick_category() -> InlineKeyboardMarkup:
    cats = [
        "Еда и напитки","Алкоголь","Транспорт","Связь и интернет",
        "Подписки","Коммунальные платежи","Развлечения",
        "Домашние расходы","Здоровье","Одежда","Прочие платежи","Доход"
    ]
    rows, row = [], []
    for c in cats:
        row.append(InlineKeyboardButton(text=c, callback_data=f"pickcat:{c}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text="➕ Добавить свою…", callback_data="pickcat:__new__")])
    rows.append([InlineKeyboardButton(text="Пропустить", callback_data="pickcat:__skip__")])
    rows.append([InlineKeyboardButton(text="Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

_STOP_WORDS = {
    "потратил","потратила","купил","купила","оплатил","оплатила","заплатил","заплатила",
    "вчера","сегодня","на","по","за","—","-","+",
    "руб","руб.","byn","р","р.","бр","usd","eur","₽","$","€"
}

def extract_term(text: str) -> str:
    if not text:
        return ""
    s = text.lower()
    s = re.sub(r"\b\d+[.,]?\d*\b", " ", s)
    s = re.sub(r"\b(byn|бр|р\.?|руб\.?|руб|₽|usd|\$|eur|€)\b", " ", s)
    s = re.sub(r"[+–—-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    words = [w for w in re.findall(r"[a-zа-яё][a-zа-яё0-9\-]*", s) if w not in _STOP_WORDS]
    if not words:
        return ""
    return " ".join(w.capitalize() for w in words[:3])

def clean_name(desc: str, fallback: str) -> str:
    if not desc:
        return fallback
    m = re.search(r"[A-Za-zА-Яа-яЁё]+[A-Za-zА-Яа-яЁё0-9\-]*", desc.strip())
    if not m:
        return fallback
    return (m.group(0) or fallback).capitalize()
