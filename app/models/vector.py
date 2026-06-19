from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"

    embedding_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chunk_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_chunks.chunk_id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(64), nullable=False, default="bge-m3")
    dimension: Mapped[int] = mapped_column(Integer, nullable=False, default=1024)
    vector: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chunk = relationship("DocumentChunk")
