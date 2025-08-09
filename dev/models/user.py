# app/models/user.py
# Объявляем Base и модель User (совместимо с Operation). Добавлены: currency, daily_limit.

from __future__ import annotations

from sqlalchemy import Column, Integer, BigInteger, String, Float
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=True)
    language = Column(String(10), default="ru")
    currency = Column(String(10), default="BYN")      # для будущего форматирования
    daily_limit = Column(Float, nullable=True)        # необязательный дневной лимит расходов

    operations = relationship("Operation", back_populates="user")
