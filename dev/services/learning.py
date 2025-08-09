# -*- coding: utf-8 -*-
# app/services/learning.py
"""
Персональное обучение терминов (слово -> категория) в JSON, как в старом боте.

Структура app/data/categories.json:
{
  "global": { "капучино": "Еда и напитки" },
  "users":  { "123456789": { "кириешки": "Еда и напитки" } }
}
"""
from __future__ import annotations
import json
import difflib
from pathlib import Path
from typing import Optional, Dict

# Файл лежит в app/data/categories.json
ROOT = Path(__file__).resolve().parents[1]  # -> app/
DATA_PATH = ROOT / "data" / "categories.json"

def _ensure_store() -> Dict:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_PATH.exists():
        DATA_PATH.write_text(json.dumps({"global": {}, "users": {}}, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8") or "{}")
    except Exception:
        DATA_PATH.write_text(json.dumps({"global": {}, "users": {}}, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"global": {}, "users": {}}

def _save_store(store: Dict) -> None:
    DATA_PATH.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")

def normalize_term(term: str) -> str:
    return (term or "").strip().lower()

def get_learned_category(user_id: int, term: str) -> Optional[str]:
    """Вернёт категорию по слову с учётом пользователя. Поддерживает нечёткие совпадения."""
    store = _ensure_store()
    t = normalize_term(term)
    users = store.get("users", {})
    user_map: Dict[str, str] = users.get(str(user_id), {})
    global_map: Dict[str, str] = store.get("global", {})

    if t in user_map:
        return user_map[t]
    if t in global_map:
        return global_map[t]

    if user_map:
        cand = difflib.get_close_matches(t, user_map.keys(), n=1, cutoff=0.88)
        if cand:
            return user_map[cand[0]]
    if global_map:
        cand = difflib.get_close_matches(t, global_map.keys(), n=1, cutoff=0.9)
        if cand:
            return global_map[cand[0]]
    return None

def save_user_term(user_id: int, term: str, category: str, *, global_scope: bool = False) -> None:
    """Сохранить термин -> категория. По умолчанию только для пользователя."""
    store = _ensure_store()
    t = normalize_term(term)
    cat = (category or "").strip()
    if not t or not cat:
        return

    if global_scope:
        store.setdefault("global", {})[t] = cat
    else:
        users = store.setdefault("users", {})
        users.setdefault(str(user_id), {})[t] = cat

    _save_store(store)
