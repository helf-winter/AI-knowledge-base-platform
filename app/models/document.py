from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    parse_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    visibility: Mapped[str] = mapped_column(String(32), default="private")
    visibility_type: Mapped[str] = mapped_column(String(32), default="private", server_default="private")
    knowledge_space: Mapped[str] = mapped_column(String(32), nullable=False, default="personal", server_default="personal")
    visibility_scope: Mapped[str | None] = mapped_column(String(128), nullable=True)
    allowed_job_categories: Mapped[str | None] = mapped_column(Text, nullable=True)
    knowledge_category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    publish_status: Mapped[str] = mapped_column(String(32), nullable=False, default="none", server_default="none")
    allowed_departments: Mapped[str | None] = mapped_column(Text, nullable=True)
    min_permission_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    security_level: Mapped[str] = mapped_column(String(32), nullable=False, default="internal", server_default="internal")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    document_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    chunk_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.document_id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_section_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    overlap_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="zh")
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped[Document] = relationship(back_populates="chunks")


class Feedback(Base):
    __tablename__ = "feedbacks"

    feedback_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    answer_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    is_helpful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    issue_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentAccessGrant(Base):
    __tablename__ = "document_access_grants"

    grant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.document_id", ondelete="CASCADE"), index=True, nullable=False)
    granted_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AccessRequest(Base):
    __tablename__ = "access_requests"

    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.document_id", ondelete="CASCADE"), index=True, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    business_purpose: Mapped[str] = mapped_column(Text, nullable=False)
    expected_duration: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    ai_suggestion: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KnowledgePublishRequest(Base):
    __tablename__ = "knowledge_publish_requests"

    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.document_id", ondelete="CASCADE"), index=True, nullable=False)
    requester_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    target_category: Mapped[str] = mapped_column(String(128), nullable=False)
    allowed_job_categories: Mapped[str] = mapped_column(Text, nullable=False)
    publish_reason: Mapped[str] = mapped_column(Text, nullable=False)
    business_purpose: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


from app.models.core import KnowledgeMetadata  # noqa: E402
