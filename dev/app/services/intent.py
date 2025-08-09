# app/services/parser/intent.py
from __future__ import annotations

def detect_intent(text: str) -> str:
    """
    Пока две ветки: add_record | report | balance.
    Остальное позже.
    """
    t = text.lower().strip()
    if t.startswith("/") and t in ("/report", "/records", "/balance", "/start", "/help", "/cancel"):
        return "command"
    if any(w in t for w in ("отчет", "отчёт", "сколько")):
        return "report"
    if "баланс" in t:
        return "balance"
    return "add_record"
