# app/main.py
from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties  # <-- важно

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.db import init_db
from app.core.scheduler import start_scheduler


async def _set_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Запуск и онбординг"),
        BotCommand(command="help", description="Что я умею"),
        BotCommand(command="records", description="Траты/доходы за сегодня"),
        BotCommand(command="report", description="Отчёт за период"),
        BotCommand(command="balance", description="Баланс"),
        BotCommand(command="remind", description="Создать напоминание"),
        BotCommand(command="reminders", description="Список напоминаний на сегодня"),
        BotCommand(command="recurring_help", description="Справка по рекуррентным операциям"),
        BotCommand(command="export", description="Экспорт XLSX"),
        BotCommand(command="export_pdf", description="Экспорт PDF"),
        BotCommand(command="cancel", description="Отмена"),
    ]
    await bot.set_my_commands(commands)


def _register_handlers(dp: Dispatcher) -> None:
    try:
        from app.handlers import setup as setup_handlers  # type: ignore
        setup_handlers(dp)
    except Exception as e:
        logging.warning("Handlers are not wired yet: %s", e)


async def main() -> None:
    setup_logging(settings.log_level)
    await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),  # <-- вот так
    )
    dp = Dispatcher()

    _register_handlers(dp)
    await _set_bot_commands(bot)

    start_scheduler(bot)

    logging.info("Bot starting polling…")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        with suppress(Exception):
            await bot.session.close()
        logging.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
