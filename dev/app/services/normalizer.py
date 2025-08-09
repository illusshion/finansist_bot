# app/services/parser/normalizer.py
from __future__ import annotations
import re

_ws_re = re.compile(r"\s+")
def normalize(text: str) -> str:
    t = text.strip()
    t = t.replace(",", ".")  # 10,5 -> 10.5
    t = _ws_re.sub(" ", t)
    return t
