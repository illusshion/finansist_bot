# app/services/parser/resolver.py
from __future__ import annotations
from typing import Optional, Dict, Any

from .normalizer import normalize
from .amount import extract_amount, detect_type
from .category import detect_category
from .intent import detect_intent

def parse_message(text: str) -> Optional[Dict[str, Any]]:
    """
    Возвращает dict:
    {
      amount: float,
      currency: "BYN",
      type: "income"|"expense",
      category: str,
      product: str,
      raw: str,
      intent: str
    }
    Или None, если суммы нет.
    """
    t = normalize(text)
    amt = extract_amount(t)
    if not amt:
        return None
    amount, currency = amt
    op_type = detect_type(t)
    category = detect_category(t, op_type)
    # продукт = первое слово без знака/цифр
    product = next((w for w in t.split() if not w.startswith(("+","-")) and not w.replace(".","").isdigit()), "")
    return {
        "amount": amount,
        "currency": currency,
        "type": op_type,
        "category": category,
        "product": product,
        "raw": text.strip(),
        "intent": detect_intent(t),
    }
