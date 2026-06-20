"""upgrade knowledge merge agent

Revision ID: 0022_merge_agent_upgrade
Revises: 0021_knowledge_merge_suggestions
Create Date: 2026-06-20 16:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0022_merge_agent_upgrade"
down_revision = "0021_knowledge_merge_suggestions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("knowledge_merge_suggestions")}
    if "generation_method" not in columns:
        op.add_column(
            "knowledge_merge_suggestions",
            sa.Column("generation_method", sa.String(length=32), server_default="rule_fallback", nullable=False),
        )
    if "conflict_notes" not in columns:
        op.add_column("knowledge_merge_suggestions", sa.Column("conflict_notes", sa.Text(), nullable=True))
    if "source_attributions" not in columns:
        op.add_column("knowledge_merge_suggestions", sa.Column("source_attributions", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("knowledge_merge_suggestions", "source_attributions")
    op.drop_column("knowledge_merge_suggestions", "conflict_notes")
    op.drop_column("knowledge_merge_suggestions", "generation_method")
