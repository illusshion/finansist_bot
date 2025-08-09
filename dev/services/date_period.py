# app/services/date_period.py
# Разбор периода: сегодня/вчера/неделя/месяц/за N дней/имена месяцев (рус).

from __future__ import annotations
from datetime import date, timedelta
from typing import Tuple
import re

RU_MONTHS = {
    1: "январ", 2: "феврал", 3: "март", 4: "апрел",
    5: "май", 6: "июн", 7: "июл", 8: "август",
    9: "сентябр", 10: "октябр", 11: "ноябр", 12: "декабр",
}

MONTH_KEYS = {v: k for k, v in RU_MONTHS.items()}  # по префиксу

def _month_from_text(t: str) -> int | None:
    for stem, mnum in MONTH_KEYS.items():
        if stem in t:
            return mnum
    return None

def period_from_text(text: str) -> Tuple[date, date, str]:
    t = (text or "").lower()
    t = re.sub(r"\s+", " ", t).strip()
    today = date.today()

    if "вчера" in t:
        d = today - timedelta(days=1)
        return d, d, "вчера"

    if "недел" in t or "7 д" in t:
        start = today - timedelta(days=6)
        return start, today, "за неделю"

    if "месяц" in t:
        start = today.replace(day=1)
        if start.month == 12:
            end = date(start.year, 12, 31)
        else:
            end = (start.replace(month=start.month + 1, day=1) - timedelta(days=1))
        return start, end, "за месяц"

    # за N дней / за N д / 3 дня / 3д
    m = re.search(r"(за\s*)?(\d+)\s*(дн|д|дня|дней)", t)
    if m:
        n = max(1, int(m.group(2)))
        start = today - timedelta(days=n - 1)
        return start, today, f"за {n} дней"

    # конкретный месяц по названию (текущий год)
    mnum = _month_from_text(t)
    if mnum:
        start = date(today.year, mnum, 1)
        if mnum == 12:
            end = date(today.year, 12, 31)
        else:
            end = date(today.year, mnum + 1, 1) - timedelta(days=1)
        # человек мог написать «август отчёт» или «отчёт за август»
        return start, end, f"за {RU_MONTHS[mnum]}"

    # по умолчанию — сегодня
    return today, today, "сегодня"
