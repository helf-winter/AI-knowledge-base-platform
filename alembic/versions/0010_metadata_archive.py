"""add archive fields to knowledge metadata

Revision ID: 0010_metadata_archive
Revises: 0009_agent_skills
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_metadata_archive"
down_revision = "0009_agent_skills"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("knowledge_metadata")}

    if "is_archived" not in columns:
        op.add_column(
            "knowledge_metadata",
            sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        )
    if "deleted_at" not in columns:
        op.add_column("knowledge_metadata", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("knowledge_metadata")}

    if "deleted_at" in columns:
        op.drop_column("knowledge_metadata", "deleted_at")
    if "is_archived" in columns:
        op.drop_column("knowledge_metadata", "is_archived")
