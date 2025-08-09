# app/models/recurring.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.models.user import Base

class RecurringOp(Base):
    __tablename__ = "recurring_ops"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    # параметры операции
    amount = Column(Float, nullable=False)             # абсолютная величина
    category = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    op_type = Column(String(10), nullable=False)       # "income" | "expense"

    # расписание
    period = Column(String(10), nullable=False)        # "daily" | "weekly" | "monthly"
    hour = Column(Integer, nullable=False)             # 0-23
    minute = Column(Integer, nullable=False)           # 0-59
    dow = Column(Integer, nullable=True)               # 0-6 для weekly (понедельник=0)
    dom = Column(Integer, nullable=True)               # 1-28 для monthly (без заморочек с концом мес.)

    next_run = Column(DateTime, nullable=False, index=True)  # ближайший запуск

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")
