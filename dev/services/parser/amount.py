# app/services/parser/amount.py
# Извлечение суммы и определение типа операции.

from __future__ import annotations
import re
from typing import Tuple, Optional

# Ищем первое число с необязательным знаком.
# Допускаем разделитель запятая/точка, пробелы как разделители тысяч убираем заранее в normalizer.
_RX_NUM = re.compile(r"(?P<sign>[+-])?\s*(?P<num>\d+(?:\.\d{1,2})?)")

def extract_amount(text: str) -> Optional[Tuple[float, str]]:
    """
    Возвращает (amount, currency). Валюта пока фиксированная "BYN".
    Ищет ПЕРВОЕ число в строке (включая знак).
    Примеры:
      "еда 10"        -> (10.0, "BYN")
      "-5 такси"      -> (5.0, "BYN")
      "+200 партнерка"-> (200.0, "BYN")
    """
    if not text:
        return None
    m = _RX_NUM.search(text)
    if not m:
        return None
    num = float(m.group("num"))
    # Возвращаем абсолютное значение — знак учитывается в detect_type
    return (abs(num), "BYN")

def detect_type(text: str) -> str:
    """
    Определяет тип операции.
      - Если есть явный '+' перед числом — income
      - Если есть явный '-' перед числом — expense
      - Иначе по эвристике: слова про доход → income, иначе expense
    """
    if not text:
        return "expense"
    m = _RX_NUM.search(text)
    if m and m.group("sign"):
        return "income" if m.group("sign") == "+" else "expense"

    t = text.lower()
    income_markers = ("зарплат", "доход", "прибыль", "прем", "партнер", "партнёр", "кешбек", "кэшбек", "cashback", "вернули")
    if any(k in t for k in income_markers):
        return "income"
    return "expense"
