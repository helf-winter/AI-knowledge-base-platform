"""switch chunk embeddings to bge m3 dimension

Revision ID: 0019_bge_m3_embeddings
Revises: 0018_public_suggestions
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision = "0019_bge_m3_embeddings"
down_revision = "0018_public_suggestions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "chunk_embeddings" not in inspector.get_table_names():
        return

    op.execute("DROP INDEX IF EXISTS ix_chunk_embeddings_vector_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_chunk_embeddings_vector_ivfflat")
    op.execute("DELETE FROM chunk_embeddings")
    op.alter_column("chunk_embeddings", "dimension", server_default=sa.text("1024"))
    op.alter_column(
        "chunk_embeddings",
        "vector",
        existing_type=Vector(64),
        type_=Vector(1024),
        postgresql_using="vector::vector(1024)",
        existing_nullable=False,
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunk_embeddings_vector_hnsw ON chunk_embeddings USING hnsw (vector vector_cosine_ops)")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "chunk_embeddings" not in inspector.get_table_names():
        return

    op.execute("DROP INDEX IF EXISTS ix_chunk_embeddings_vector_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_chunk_embeddings_vector_ivfflat")
    op.execute("DELETE FROM chunk_embeddings")
    op.alter_column("chunk_embeddings", "dimension", server_default=sa.text("64"))
    op.alter_column(
        "chunk_embeddings",
        "vector",
        existing_type=Vector(1024),
        type_=Vector(64),
        postgresql_using="vector::vector(64)",
        existing_nullable=False,
    )
