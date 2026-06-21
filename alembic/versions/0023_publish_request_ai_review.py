"""add publish request ai review fields

Revision ID: 0023_publish_ai_review
Revises: 0022_merge_agent_upgrade
Create Date: 2026-06-22 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0023_publish_ai_review"
down_revision = "0022_merge_agent_upgrade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("knowledge_publish_requests")}
    if "ai_suggestion" not in columns:
        op.add_column("knowledge_publish_requests", sa.Column("ai_suggestion", sa.String(length=32), nullable=True))
    if "ai_risk_level" not in columns:
        op.add_column("knowledge_publish_requests", sa.Column("ai_risk_level", sa.String(length=32), nullable=True))
    if "ai_reason" not in columns:
        op.add_column("knowledge_publish_requests", sa.Column("ai_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("knowledge_publish_requests", "ai_reason")
    op.drop_column("knowledge_publish_requests", "ai_risk_level")
    op.drop_column("knowledge_publish_requests", "ai_suggestion")
