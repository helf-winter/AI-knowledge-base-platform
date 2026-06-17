"""add trace id to conversation turns

Revision ID: 0011_conversation_trace
Revises: 0010_metadata_archive
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_conversation_trace"
down_revision = "0010_metadata_archive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("conversation_turns")}

    if "trace_id" not in columns:
        op.add_column("conversation_turns", sa.Column("trace_id", sa.String(length=36), nullable=True))

    indexes = {index["name"] for index in inspector.get_indexes("conversation_turns")}
    if "ix_conversation_turns_trace_id" not in indexes:
        op.create_index("ix_conversation_turns_trace_id", "conversation_turns", ["trace_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("conversation_turns")}
    columns = {column["name"] for column in inspector.get_columns("conversation_turns")}

    if "ix_conversation_turns_trace_id" in indexes:
        op.drop_index("ix_conversation_turns_trace_id", table_name="conversation_turns")
    if "trace_id" in columns:
        op.drop_column("conversation_turns", "trace_id")
