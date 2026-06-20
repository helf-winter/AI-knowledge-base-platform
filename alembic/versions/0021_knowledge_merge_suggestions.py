"""add knowledge merge suggestions

Revision ID: 0021_knowledge_merge_suggestions
Revises: 0020_task_progress_fields
Create Date: 2026-06-20 10:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0021_knowledge_merge_suggestions"
down_revision = "0020_task_progress_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "knowledge_merge_suggestions" not in inspector.get_table_names():
        op.create_table(
            "knowledge_merge_suggestions",
            sa.Column("suggestion_id", sa.String(length=36), nullable=False),
            sa.Column("source_document_ids", sa.Text(), nullable=False),
            sa.Column("suggested_title", sa.String(length=255), nullable=False),
            sa.Column("suggested_category", sa.String(length=128), nullable=True),
            sa.Column("suggested_outline", sa.Text(), nullable=True),
            sa.Column("suggested_content", sa.Text(), nullable=False),
            sa.Column("similarity_reason", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
            sa.Column("requester_id", sa.String(length=36), nullable=True),
            sa.Column("reviewed_by", sa.String(length=36), nullable=True),
            sa.Column("review_comment", sa.Text(), nullable=True),
            sa.Column("merged_document_id", sa.String(length=36), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["merged_document_id"], ["documents.document_id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("suggestion_id"),
        )
    indexes = {index["name"] for index in inspector.get_indexes("knowledge_merge_suggestions")}
    if "ix_knowledge_merge_suggestions_requester_id" not in indexes:
        op.create_index("ix_knowledge_merge_suggestions_requester_id", "knowledge_merge_suggestions", ["requester_id"])
    if "ix_knowledge_merge_suggestions_merged_document_id" not in indexes:
        op.create_index("ix_knowledge_merge_suggestions_merged_document_id", "knowledge_merge_suggestions", ["merged_document_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_merge_suggestions_merged_document_id", table_name="knowledge_merge_suggestions")
    op.drop_index("ix_knowledge_merge_suggestions_requester_id", table_name="knowledge_merge_suggestions")
    op.drop_table("knowledge_merge_suggestions")
