"""add cluster_key to knowledge_gaps

Revision ID: 0008_knowledge_gaps
Revises: 0007_merge_heads
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_knowledge_gaps"
down_revision = "0007_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("knowledge_gaps"):
        op.create_table(
            "knowledge_gaps",
            sa.Column("gap_id", sa.String(length=36), primary_key=True),
            sa.Column("query_text", sa.Text(), nullable=False),
            sa.Column("session_id", sa.String(length=36), nullable=True),
            sa.Column("user_id", sa.String(length=36), nullable=True),
            sa.Column("answer_id", sa.String(length=36), nullable=True),
            sa.Column("issue_type", sa.String(length=64), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("evidence", sa.Text(), nullable=True),
            sa.Column("suggested_title", sa.String(length=255), nullable=True),
            sa.Column("suggested_content", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("cluster_key", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_knowledge_gaps_session_id", "knowledge_gaps", ["session_id"])
        op.create_index("ix_knowledge_gaps_user_id", "knowledge_gaps", ["user_id"])
        op.create_index("ix_knowledge_gaps_answer_id", "knowledge_gaps", ["answer_id"])
    else:
        columns = {column["name"] for column in inspector.get_columns("knowledge_gaps")}
        if "cluster_key" not in columns:
            op.add_column("knowledge_gaps", sa.Column("cluster_key", sa.String(length=128), nullable=True))

    indexes = {index["name"] for index in inspector.get_indexes("knowledge_gaps")}
    if "ix_knowledge_gaps_cluster_key" not in indexes:
        op.create_index("ix_knowledge_gaps_cluster_key", "knowledge_gaps", ["cluster_key"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_gaps_cluster_key", table_name="knowledge_gaps")
    op.drop_column("knowledge_gaps", "cluster_key")
