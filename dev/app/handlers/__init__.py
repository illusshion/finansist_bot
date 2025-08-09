# app/handlers/__init__.py
from __future__ import annotations

from typing import Iterable
from aiogram import Dispatcher, Router
import logging
import traceback

LOADED_HANDLERS: list[str] = []
FAILED_HANDLERS: dict[str, str] = {}

def _module_names() -> Iterable[str]:
    # ПОРЯДОК ВАЖЕН: reports раньше records, чтобы NL-"отчёт..." не съедал фри-инпут
    return (
        "start",
        "reports",   # <-- раньше
        "records",   # <-- позже
        "balance",
        "search",
        "reminders",
        "recurring",
        "export",
        "settings",
        "admin",
    )

def setup(dp: Dispatcher) -> None:
    for name in _module_names():
        try:
            mod = __import__(f"app.handlers.{name}", fromlist=["router"])
            router: Router = getattr(mod, "router")
            dp.include_router(router)
            LOADED_HANDLERS.append(name)
            logging.info('handler_loaded name="%s"', name)
        except Exception as e:
            tb = traceback.format_exc()
            FAILED_HANDLERS[name] = f"{e.__class__.__name__}: {e}\n{tb}"
            logging.exception('handler_failed name="%s"', name)
