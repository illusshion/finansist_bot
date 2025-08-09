# -*- coding: utf-8 -*-
# app/services/periods.py
from __future__ import annotations
from datetime import date, datetime, timedelta
import re
from typing import Optional, Tuple

RU_MONTHS = {
    "янв": 1, "январ": 1,
    "фев": 2, "феврал": 2,
    "мар": 3, "март": 3,
    "апр": 4, "апрел": 4,
    "мая": 5, "май": 5,
    "июн": 6, "июнь": 6,
    "июл": 7, "июль": 7,
    "авг": 8, "август": 8,
    "сен": 9, "сентяб": 9,
    "окт": 10,"октябр": 10,
    "ноя": 11,"ноябр": 11,
    "дек": 12,"декабр": 12,
}

def today() -> date:
    return datetime.now().date()

def fmt_date(d: date) -> str:
    return d.strftime("%Y-%m-%d")

def period_preset(kind: str) -> tuple[date, date]:
    t = today()
    if kind == "day":
        return (t, t)
    if kind == "week":
        return (t - timedelta(days=6), t)
    if kind == "month":
        first = t.replace(day=1)
        return (first, t)
    raise ValueError("unknown preset")

def label_for_period(d1: date, d2: date, label_override: Optional[str]) -> str:
    if label_override:
        return label_override
    if d1 == d2:
        return d1.isoformat()
    return f"{d1.isoformat()} — {d2.isoformat()}"

def _parse_month_token(tok: str) -> Optional[int]:
    s = tok.lower()
    for k, m in RU_MONTHS.items():
        if s.startswith(k):
            return m
    return None

def parse_free_period(text: str) -> Optional[Tuple[date, date, str]]:
    """
    Понимает:
      - "отчет/отчёт за 3 дня"
      - "за неделю" / "неделя"
      - "за месяц" / "месяц" (текущий)
      - "за август" (текущий год)
      - "с 5 по 7 августа"
      - "сегодня" / "вчера"
    Возвращает (d1, d2, label).
    """
    if not text:
        return None
    s = text.lower().strip()

    # сегодня/вчера
    if "сегодня" in s:
        d = today(); return (d, d, "сегодня")
    if "вчера" in s:
        d = today() - timedelta(days=1); return (d, d, "вчера")

    # за N дней
    m = re.search(r"за\s+(\d+)\s*д", s)
    if m:
        n = max(1, int(m.group(1)))
        d2 = today()
        d1 = d2 - timedelta(days=n - 1)
        return (d1, d2, f"последние {n} дн.")

    # неделя / за неделю
    if "недел" in s:
        d2 = today()
        d1 = d2 - timedelta(days=6)
        return (d1, d2, "последнюю неделю")

    # месяц / за месяц
    if "месяц" in s:
        d2 = today()
        d1 = d2.replace(day=1)
        return (d1, d2, "месяц")

    # за <месяц>
    m = re.search(r"за\s+([A-Za-zА-Яа-яЁё]+)", s)
    if m:
        mon = _parse_month_token(m.group(1))
        if mon:
            t = today()
            y = t.year
            d1 = date(y, mon, 1)
            if mon == 12:
                d2 = date(y, 12, 31)
            else:
                d2 = date(y, mon + 1, 1) - timedelta(days=1)
            return (d1, d2, m.group(1).capitalize())

    # с D по D <месяц>
    m = re.search(r"с\s*(\d{1,2})\s*по\s*(\d{1,2})\s*([A-Za-zА-Яа-яЁё]+)", s)
    if m:
        d1d, d2d, mon_tok = int(m.group(1)), int(m.group(2)), m.group(3)
        mon = _parse_month_token(mon_tok)
        if mon:
            y = today().year
            d1 = date(y, mon, d1d)
            d2 = date(y, mon, d2d)
            if d1 > d2:
                d1, d2 = d2, d1
            return (d1, d2, f"{d1.isoformat()}–{d2.isoformat()}")

    # просто "отчет/отчёт" — сегодня
    if "отчет" in s or "отчёт" in s or "статист" in s or "сводк" in s:
        d = today(); return (d, d, "сегодня")

    return None
