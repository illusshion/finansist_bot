# app/ui/keyboards.py
from __future__ import annotations
from typing import List, Tuple
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def deletion_keyboard(pairs: List[Tuple[str, int]]) -> InlineKeyboardMarkup:
    """
    pairs: [(label, op_id), ...]
    по 2 в ряд + кнопка "Отмена"
    """
    buttons = []
    row = []
    for label, op_id in pairs:
        row.append(InlineKeyboardButton(text=label, callback_data=f"del:{op_id}"))
        if len(row) == 2:
            buttons.append(row); row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Отмена", callback_data="del:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
