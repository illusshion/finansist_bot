# app/handlers/start.py
# Онбординг (/start) и справка (/help, /cancel)

from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name=__name__)


@router.message(CommandStart())
async def cmd_start(m: Message) -> None:
    # Здесь позже добавим create_or_get_user() после переноса моделей/репозитория
    text = (
        "👋 Привет! Я помогу вести личные финансы.\n\n"
        "<b>Как пользоваться:</b>\n"
        "• Пиши простым текстом: <code>еда 10</code>, <code>такси -7</code>, <code>+200 фриланс</code>.\n"
        "• Я сам определю сумму, тип операции и категорию.\n\n"
        "<b>Команды:</b>\n"
        "/records — показать операции за сегодня (с удалением)\n"
        "/report — отчёт за период\n"
        "/balance — текущий баланс\n"
        "/cancel — отменить диалог\n"
        "/help — справка"
    )
    await m.answer(text, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(m: Message) -> None:
    text = (
        "📘 <b>Справка</b>\n\n"
        "Записи без команд:\n"
        "• <code>сигареты 5</code>\n"
        "• <code>вчера такси 12</code>\n"
        "• <code>+200 партнерка</code>\n\n"
        "Запросы:\n"
        "• <code>отчёт за неделю</code>\n"
        "• <code>сколько на еду сегодня</code>\n\n"
        "Команды:\n"
        "/records, /report, /balance, /cancel, /help"
    )
    await m.answer(text, parse_mode="HTML")


@router.message(Command("cancel"))
@router.message(F.text.lower() == "отмена")
async def cmd_cancel(m: Message) -> None:
    await m.answer("Ок, отменил. Продолжаем.", parse_mode="HTML")
