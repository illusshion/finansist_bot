# app/services/parser/resolver.py
# Единая точка входа парсера: parse_message(...)
from __future__ import annotations
import re
from typing import Optional

from .normalizer import normalize
from .amount import extract_amount, detect_type
from .category import detect_category

# Число со знаком/без знака (первое в строке)
_RX_NUM_POS = re.compile(r"(?P<sign>[+-])?\s*(?P<num>\d+(?:\.\d{1,2})?)")

def _extract_product_phrase(text: str) -> str:
    """
    Берём «продукт» как фразу ДО первой суммы.
    Примеры:
      "квас лидский 5" -> "квас лидский"
      "такси -7"       -> "такси"
      "+200 фриланс"   -> "фриланс"
      "вчера такси 10" -> "вчера такси" (дальше категория разрулит)
    Если суммы нет — вернёт пусто (но мы в parse_message проверяем, что сумма есть).
    """
    m = _RX_NUM_POS.search(text)
    if not m:
        return ""
    before = text[:m.start()].strip()
    if before:
        # убираем лишние пробелы
        before = re.sub(r"\s+", " ", before)
    else:
        # если сумма стоит первой — берём всё после числа как продукт
        after = text[m.end():].strip()
        before = re.sub(r"\s+", " ", after)
    return before

def parse_message(raw: str, user_tg_id: int | None = None) -> Optional[dict]:
    """
    На вход свободный текст, на выход:
      { amount, currency, type, category, product, raw }
    Если суммы нет — None.
    """
    if not raw or not raw.strip():
        return None

    text = normalize(raw)
    amt_cur = extract_amount(text)
    if not amt_cur:
        return None
    amount, currency = amt_cur

    op_type = detect_type(text)
    product = _extract_product_phrase(text) or ""
    category = detect_category(text, op_type=op_type)

    return {
        "amount": float(abs(amount)),
        "currency": (currency or "BYN"),
        "type": op_type,           # "income" | "expense"
        "category": category,      # неизвестное -> "Прочее" (далее обучим)
        "product": product,        # ФРАЗА (может быть из 2+ слов)
        "raw": raw.strip(),
    }
