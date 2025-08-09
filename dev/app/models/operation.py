# app/models/operation.py
# Модель Operation 1-в-1 совместима с твоим старым кодом.

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.models.user import Base


class Operation(Base):
    __tablename__ = "operations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    type = Column(String(10), nullable=False)  # 'income' | 'expense'
    created_at = Column(DateTime, default=datetime.utcnow)

    # связи
    user = relationship("User", back_populates="operations")
