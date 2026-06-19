"""add public knowledge suggestions

Revision ID: 0018_public_suggestions
Revises: 0017_fix_feedback_links
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa


revision = "0018_public_suggestions"
down_revision = "0017_fix_feedback_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "public_knowledge_suggestions" in inspector.get_table_names():
        return

    op.create_table(
        "public_knowledge_suggestions",
        sa.Column("suggestion_id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False),
        sa.Column("public_ref_id", sa.String(length=36), sa.ForeignKey("public_knowledge_refs.ref_id", ondelete="SET NULL"), nullable=True),
        sa.Column("requester_id", sa.String(length=36), nullable=False),
        sa.Column("suggestion_type", sa.String(length=64), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=False),
        sa.Column("business_impact", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", sa.String(length=36), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_public_knowledge_suggestions_document_id", "public_knowledge_suggestions", ["document_id"])
    op.create_index("ix_public_knowledge_suggestions_public_ref_id", "public_knowledge_suggestions", ["public_ref_id"])
    op.create_index("ix_public_knowledge_suggestions_requester_id", "public_knowledge_suggestions", ["requester_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "public_knowledge_suggestions" not in inspector.get_table_names():
        return

    op.drop_index("ix_public_knowledge_suggestions_requester_id", table_name="public_knowledge_suggestions")
    op.drop_index("ix_public_knowledge_suggestions_public_ref_id", table_name="public_knowledge_suggestions")
    op.drop_index("ix_public_knowledge_suggestions_document_id", table_name="public_knowledge_suggestions")
    op.drop_table("public_knowledge_suggestions")
