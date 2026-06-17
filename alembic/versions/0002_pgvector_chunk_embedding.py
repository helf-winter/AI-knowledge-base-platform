"""add pgvector chunk embedding

Revision ID: 0002_pgvector_chunk_embedding
Revises: 0001_init_base_tables
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0002_pgvector_chunk_embedding"
down_revision = "0001_init_base_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.create_table(
        "chunk_embeddings",
        sa.Column("embedding_id", sa.String(length=36), primary_key=True),
        sa.Column("chunk_id", sa.String(length=36), sa.ForeignKey("document_chunks.chunk_id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("embedding_model", sa.String(length=64), nullable=False, server_default="bge-m3"),
        sa.Column("dimension", sa.Integer(), nullable=False, server_default="64"),
        sa.Column("vector", Vector(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_chunk_embeddings_chunk_id", "chunk_embeddings", ["chunk_id"])

    # Create pgvector indexes only when the extension is available in PostgreSQL.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunk_embeddings_vector_hnsw ON chunk_embeddings USING hnsw (vector vector_cosine_ops) WITH (m = 16, ef_construction = 64);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunk_embeddings_vector_ivfflat ON chunk_embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunk_embeddings_vector_ivfflat;")
    op.execute("DROP INDEX IF EXISTS ix_chunk_embeddings_vector_hnsw;")
    op.drop_index("ix_chunk_embeddings_chunk_id", table_name="chunk_embeddings")
    op.drop_table("chunk_embeddings")
