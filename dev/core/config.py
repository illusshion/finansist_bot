# app/core/config.py
# Конфиг без магии: читаем .env, валидируем минимально, отдаём типизированный объект.
from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Загружаем переменные окружения из .env в корне dev/
# Пример .env:
# BOT_TOKEN=123:ABC
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/finansist
# OWNER_IDS=5969047567,1000758079
# TZ=Europe/Minsk
load_dotenv()

def _parse_owner_ids(raw: str | None) -> list[int]:
    if not raw:
        return []
    out: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if part.isdigit():
            out.append(int(part))
        else:
            # допускаем случайные пробелы и мусор
            num = "".join(ch for ch in part if ch.isdigit())
            if num:
                out.append(int(num))
    return out

@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_url: str
    owner_ids: list[int]
    tz: str
    log_level: str

    @staticmethod
    def load() -> "Settings":
        bot_token = os.getenv("BOT_TOKEN", "").strip()
        database_url = os.getenv("DATABASE_URL", "").strip()
        owner_ids = _parse_owner_ids(os.getenv("OWNER_IDS"))
        tz = os.getenv("TZ", "Europe/Minsk").strip()
        log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()

        # Жёсткая валидация критичных полей
        if not bot_token:
            raise RuntimeError("BOT_TOKEN не задан в .env")
        if not database_url:
            raise RuntimeError("DATABASE_URL не задан в .env")
        return Settings(
            bot_token=bot_token,
            database_url=database_url,
            owner_ids=owner_ids,
            tz=tz,
            log_level=log_level,
        )

settings = Settings.load()
