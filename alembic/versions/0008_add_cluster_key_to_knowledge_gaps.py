"""add cluster_key to knowledge_gaps

Revision ID: 0008_add_cluster_key_to_knowledge_gaps
Revises: 0007_merge_heads
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_add_cluster_key_to_knowledge_gaps"
down_revision = "0007_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("knowledge_gaps", sa.Column("cluster_key", sa.String(length=128), nullable=True))
    op.create_index("ix_knowledge_gaps_cluster_key", "knowledge_gaps", ["cluster_key"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_gaps_cluster_key", table_name="knowledge_gaps")
    op.drop_column("knowledge_gaps", "cluster_key")
