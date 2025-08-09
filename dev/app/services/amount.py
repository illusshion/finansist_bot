# app/services/parser/amount.py
from __future__ import annotations
import re
from typing import Optional, Tuple

# Базовые валюты — пока игнорируем, считаем BYN по UX
_AM_RE = re.compile(r"(?P<sign>[+\-]?)\s*(?P<num>\d+(?:\.\d{1,2})?)")

def extract_amount(text: str) -> Optional[Tuple[float, str]]:
    """
    Ищем первое число, знак определяем по префиксу (+/-) если есть.
    Валюта пока константой BYN.
    """
    m = _AM_RE.search(text)
    if not m:
        return None
    sign = -1.0 if m.group("sign") == "-" else 1.0
    val = float(m.group("num")) * sign
    return abs(val), "BYN"

def detect_type(text: str) -> str:
    """
    Доход если есть + или слова «доход», «получил», «зачислили».
    Иначе расход.
    """
    t = text.lower()
    if t.startswith("+") or any(k in t for k in ("доход", "получил", "зачислили", "пришли", "пополнил", "revshare", "премия", "зарплата", "зарп", "гонорар")):
        return "income"
    return "expense"
