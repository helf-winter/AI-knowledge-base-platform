"""merge migration heads

Revision ID: 0007_merge_heads
Revises: 0002_pgvector_chunk_embedding, 0006_conversation_turns
Create Date: 2026-05-29
"""
from alembic import op

revision = "0007_merge_heads"
down_revision = ("0002_pgvector_chunk_embedding", "0006_conversation_turns")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
