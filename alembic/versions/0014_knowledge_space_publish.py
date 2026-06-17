"""add knowledge spaces and publish requests

Revision ID: 0014_knowledge_space_publish
Revises: 0013_document_access_control
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_knowledge_space_publish"
down_revision = "0013_document_access_control"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    document_columns = {column["name"] for column in inspector.get_columns("documents")}

    if "knowledge_space" not in document_columns:
        op.add_column("documents", sa.Column("knowledge_space", sa.String(length=32), nullable=False, server_default="public"))
    if "visibility_scope" not in document_columns:
        op.add_column("documents", sa.Column("visibility_scope", sa.String(length=128), nullable=True))
    if "allowed_job_categories" not in document_columns:
        op.add_column("documents", sa.Column("allowed_job_categories", sa.Text(), nullable=True))
    if "knowledge_category" not in document_columns:
        op.add_column("documents", sa.Column("knowledge_category", sa.String(length=128), nullable=True))
    if "publish_status" not in document_columns:
        op.add_column("documents", sa.Column("publish_status", sa.String(length=32), nullable=False, server_default="approved"))

    if "knowledge_publish_requests" not in inspector.get_table_names():
        op.create_table(
            "knowledge_publish_requests",
            sa.Column("request_id", sa.String(length=36), nullable=False),
            sa.Column("document_id", sa.String(length=36), nullable=False),
            sa.Column("requester_id", sa.String(length=36), nullable=False),
            sa.Column("target_category", sa.String(length=128), nullable=False),
            sa.Column("allowed_job_categories", sa.Text(), nullable=False),
            sa.Column("publish_reason", sa.Text(), nullable=False),
            sa.Column("business_purpose", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("reviewed_by", sa.String(length=36), nullable=True),
            sa.Column("review_comment", sa.Text(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["document_id"], ["documents.document_id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("request_id"),
        )
        op.create_index("ix_knowledge_publish_requests_document_id", "knowledge_publish_requests", ["document_id"])
        op.create_index("ix_knowledge_publish_requests_requester_id", "knowledge_publish_requests", ["requester_id"])
        op.create_index("ix_knowledge_publish_requests_status", "knowledge_publish_requests", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "knowledge_publish_requests" in inspector.get_table_names():
        indexes = {index["name"] for index in inspector.get_indexes("knowledge_publish_requests")}
        if "ix_knowledge_publish_requests_status" in indexes:
            op.drop_index("ix_knowledge_publish_requests_status", table_name="knowledge_publish_requests")
        if "ix_knowledge_publish_requests_requester_id" in indexes:
            op.drop_index("ix_knowledge_publish_requests_requester_id", table_name="knowledge_publish_requests")
        if "ix_knowledge_publish_requests_document_id" in indexes:
            op.drop_index("ix_knowledge_publish_requests_document_id", table_name="knowledge_publish_requests")
        op.drop_table("knowledge_publish_requests")

    document_columns = {column["name"] for column in inspector.get_columns("documents")}
    for column_name in ["publish_status", "knowledge_category", "allowed_job_categories", "visibility_scope", "knowledge_space"]:
        if column_name in document_columns:
            op.drop_column("documents", column_name)
