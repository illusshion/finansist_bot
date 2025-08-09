# app/services/parser/normalizer.py
# Нормализация входного текста перед парсингом сумм/категорий.

from __future__ import annotations
import re

_WS = re.compile(r"\s+")
_PUNCT = {
    "—": "-", "–": "-", "−": "-",  # разные минусы
    "‎": " ", "\u200b": " ", "\u00A0": " ",  # скрытые пробелы/nbsp/zwsp
}
_NUM_SEP = re.compile(r"(?<=\d)[\s_](?=\d)")  # 1 000 -> 1000

def _replace_chars(s: str) -> str:
    for src, dst in _PUNCT.items():
        s = s.replace(src, dst)
    return s

def _space_around_signs(s: str) -> str:
    # "+200", "- 10", " +  5 " -> " +200", " -10", " +5 "
    s = re.sub(r"\s*([+-])\s*(\d)", r" \1\2", s)
    # перед знаком в начале строки пробел не нужен
    return s.strip()

def normalize(text: str) -> str:
    """
    Правила:
    - нижний регистр
    - запятая в числах -> точка (10,50 -> 10.50)
    - убираем разделители тысяч (1 000 -> 1000)
    - приводим минусы к '-' и чистим невидимые символы
    - сжимаем пробелы
    Примеры:
      "Вчера такси 12,5" -> "вчера такси 12.5"
      "+ 200 Партнёрка"  -> "+200 партнёрка"
    """
    s = (text or "").strip()
    s = _replace_chars(s)
    s = s.replace(",", ".")
    s = _NUM_SEP.sub("", s)
    s = _WS.sub(" ", s)
    s = _space_around_signs(s)
    s = s.lower()
    return s
