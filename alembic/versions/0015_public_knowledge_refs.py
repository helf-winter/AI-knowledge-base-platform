"""add public knowledge references

Revision ID: 0015_public_knowledge_refs
Revises: 0014_knowledge_space_publish
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_public_knowledge_refs"
down_revision = "0014_knowledge_space_publish"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "public_knowledge_refs" in inspector.get_table_names():
        return

    op.create_table(
        "public_knowledge_refs",
        sa.Column("ref_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("publish_request_id", sa.String(length=36), nullable=True),
        sa.Column("owner_user_id", sa.String(length=36), nullable=True),
        sa.Column("target_category", sa.String(length=128), nullable=False),
        sa.Column("allowed_job_categories", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("disabled_by", sa.String(length=36), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.document_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["publish_request_id"], ["knowledge_publish_requests.request_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("ref_id"),
    )
    op.create_index("ix_public_knowledge_refs_document_id", "public_knowledge_refs", ["document_id"])
    op.create_index("ix_public_knowledge_refs_publish_request_id", "public_knowledge_refs", ["publish_request_id"])
    op.create_index("ix_public_knowledge_refs_owner_user_id", "public_knowledge_refs", ["owner_user_id"])
    op.create_index("ix_public_knowledge_refs_status", "public_knowledge_refs", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "public_knowledge_refs" not in inspector.get_table_names():
        return
    indexes = {index["name"] for index in inspector.get_indexes("public_knowledge_refs")}
    for name in [
        "ix_public_knowledge_refs_status",
        "ix_public_knowledge_refs_owner_user_id",
        "ix_public_knowledge_refs_publish_request_id",
        "ix_public_knowledge_refs_document_id",
    ]:
        if name in indexes:
            op.drop_index(name, table_name="public_knowledge_refs")
    op.drop_table("public_knowledge_refs")
