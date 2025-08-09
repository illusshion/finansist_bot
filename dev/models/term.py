# app/models/term.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Index
from sqlalchemy.orm import relationship
from app.models.user import Base

class UserTerm(Base):
    __tablename__ = "user_terms"

    id = Column(Integer, primary_key=True)
    user_tg_id = Column(BigInteger, index=True, nullable=False)
    term = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_user_terms_user_term", "user_tg_id", "term", unique=True),
    )
