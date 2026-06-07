from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KnowledgeGap(Base):
    __tablename__ = "knowledge_gaps"

    gap_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    answer_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    issue_type: Mapped[str] = mapped_column(String(64), nullable=False, default="missing_knowledge")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    suggested_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
