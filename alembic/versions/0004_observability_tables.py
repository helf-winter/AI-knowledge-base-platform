"""add observability tables

Revision ID: 0004_observability_tables
Revises: 0003_evaluation_tables
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_observability_tables"
down_revision = "0003_evaluation_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "metric_snapshots",
        sa.Column("snapshot_id", sa.String(length=36), primary_key=True),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("labels_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "alert_rules",
        sa.Column("rule_id", sa.String(length=36), primary_key=True),
        sa.Column("rule_name", sa.String(length=128), nullable=False),
        sa.Column("metric_name", sa.String(length=128), nullable=False, index=True),
        sa.Column("operator", sa.String(length=8), nullable=False, server_default=">"),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="warning"),
        sa.Column("is_enabled", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "alert_events",
        sa.Column("event_id", sa.String(length=36), primary_key=True),
        sa.Column("rule_id", sa.String(length=36), sa.ForeignKey("alert_rules.rule_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("actual_value", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    op.drop_table("alert_events")
    op.drop_table("alert_rules")
    op.drop_table("metric_snapshots")