"""add learning gap draft workflow fields

Revision ID: 0016_learning_gap_drafts
Revises: 0015_public_knowledge_refs
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_learning_gap_drafts"
down_revision = "0015_public_knowledge_refs"
branch_labels = None
depends_on = None


def _add_column_if_missing(table_name: str, existing: set[str], column: sa.Column) -> None:
    if column.name not in existing:
        op.add_column(table_name, column)
        existing.add(column.name)


def _create_index_if_missing(table_name: str, existing: set[str], name: str, columns: list[str]) -> None:
    if name not in existing:
        op.create_index(name, table_name, columns)
        existing.add(name)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "knowledge_gaps" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("knowledge_gaps")}
    _add_column_if_missing("knowledge_gaps", columns, sa.Column("normalized_question", sa.String(length=255), nullable=True))
    _add_column_if_missing("knowledge_gaps", columns, sa.Column("cluster_key", sa.String(length=64), nullable=True))
    _add_column_if_missing("knowledge_gaps", columns, sa.Column("hit_count", sa.Integer(), nullable=False, server_default="1"))
    _add_column_if_missing("knowledge_gaps", columns, sa.Column("draft_document_id", sa.String(length=36), nullable=True))
    _add_column_if_missing("knowledge_gaps", columns, sa.Column("ai_draft_content", sa.Text(), nullable=True))
    _add_column_if_missing("knowledge_gaps", columns, sa.Column("pending_confirmations", sa.Text(), nullable=True))
    _add_column_if_missing("knowledge_gaps", columns, sa.Column("admin_final_content", sa.Text(), nullable=True))
    _add_column_if_missing("knowledge_gaps", columns, sa.Column("target_category", sa.String(length=128), nullable=True))
    _add_column_if_missing("knowledge_gaps", columns, sa.Column("allowed_job_categories", sa.Text(), nullable=True))
    _add_column_if_missing("knowledge_gaps", columns, sa.Column("business_purpose", sa.Text(), nullable=True))
    _add_column_if_missing("knowledge_gaps", columns, sa.Column("review_comment", sa.Text(), nullable=True))
    _add_column_if_missing("knowledge_gaps", columns, sa.Column("reviewed_by", sa.String(length=36), nullable=True))
    _add_column_if_missing("knowledge_gaps", columns, sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))

    indexes = {index["name"] for index in inspector.get_indexes("knowledge_gaps")}
    _create_index_if_missing("knowledge_gaps", indexes, "ix_knowledge_gaps_normalized_question", ["normalized_question"])
    _create_index_if_missing("knowledge_gaps", indexes, "ix_knowledge_gaps_cluster_key", ["cluster_key"])
    _create_index_if_missing("knowledge_gaps", indexes, "ix_knowledge_gaps_draft_document_id", ["draft_document_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "knowledge_gaps" not in inspector.get_table_names():
        return

    indexes = {index["name"] for index in inspector.get_indexes("knowledge_gaps")}
    for name in [
        "ix_knowledge_gaps_draft_document_id",
        "ix_knowledge_gaps_cluster_key",
        "ix_knowledge_gaps_normalized_question",
    ]:
        if name in indexes:
            op.drop_index(name, table_name="knowledge_gaps")

    columns = {column["name"] for column in inspector.get_columns("knowledge_gaps")}
    for column_name in [
        "updated_at",
        "reviewed_by",
        "review_comment",
        "business_purpose",
        "allowed_job_categories",
        "target_category",
        "admin_final_content",
        "pending_confirmations",
        "ai_draft_content",
        "draft_document_id",
        "hit_count",
        "cluster_key",
        "normalized_question",
    ]:
        if column_name in columns:
            op.drop_column("knowledge_gaps", column_name)
