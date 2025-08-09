# app/core/logging.py
# Простая JSON-логировка в stdout + уровни

from __future__ import annotations
import logging
import sys

_JSON_FMT = (
    '{"level":"%(levelname)s","ts":"%(asctime)s",'
    '"name":"%(name)s","msg":"%(message)s"}'
)

def setup_logging(level: str = "INFO") -> None:
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(level.upper())

    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter(_JSON_FMT))
    logger.addHandler(h)
