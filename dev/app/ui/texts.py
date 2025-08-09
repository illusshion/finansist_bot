# app/ui/texts.py
from __future__ import annotations

HELP = (
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

NO_TODAY_RECORDS = "🧾 За сегодня записей нет. Ты сегодня голодал?"
DELETED = "Удалено."
CANCELLED = "Отменено"
CANT_FIND = "Не нашёл запись."
AMOUNT_MISSING = "Не вижу суммы. Напиши, например: <code>еда 10</code>."
