"""add document access control fields

Revision ID: 0013_document_access_control
Revises: 0012_employee_auth
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_document_access_control"
down_revision = "0012_employee_auth"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    document_columns = {column["name"] for column in inspector.get_columns("documents")}
    if "visibility_type" not in document_columns:
        op.add_column("documents", sa.Column("visibility_type", sa.String(length=32), nullable=False, server_default="private"))
    if "allowed_departments" not in document_columns:
        op.add_column("documents", sa.Column("allowed_departments", sa.Text(), nullable=True))
    if "min_permission_level" not in document_columns:
        op.add_column("documents", sa.Column("min_permission_level", sa.Integer(), nullable=False, server_default="1"))
    if "security_level" not in document_columns:
        op.add_column("documents", sa.Column("security_level", sa.String(length=32), nullable=False, server_default="internal"))
    if "is_public" not in document_columns:
        op.add_column("documents", sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")))
    if "document_status" not in document_columns:
        op.add_column("documents", sa.Column("document_status", sa.String(length=32), nullable=False, server_default="active"))

    if not _table_exists(inspector, "document_access_grants"):
        op.create_table(
            "document_access_grants",
            sa.Column("grant_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("document_id", sa.String(length=36), nullable=False),
            sa.Column("granted_by", sa.String(length=36), nullable=True),
            sa.Column("expire_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["document_id"], ["documents.document_id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("grant_id"),
        )
        op.create_index("ix_document_access_grants_user_id", "document_access_grants", ["user_id"])
        op.create_index("ix_document_access_grants_document_id", "document_access_grants", ["document_id"])

    if not _table_exists(inspector, "access_requests"):
        op.create_table(
            "access_requests",
            sa.Column("request_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("document_id", sa.String(length=36), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("business_purpose", sa.Text(), nullable=False),
            sa.Column("expected_duration", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("ai_suggestion", sa.String(length=32), nullable=True),
            sa.Column("ai_risk_level", sa.String(length=32), nullable=True),
            sa.Column("ai_reason", sa.Text(), nullable=True),
            sa.Column("reviewed_by", sa.String(length=36), nullable=True),
            sa.Column("review_comment", sa.Text(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["document_id"], ["documents.document_id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("request_id"),
        )
        op.create_index("ix_access_requests_user_id", "access_requests", ["user_id"])
        op.create_index("ix_access_requests_document_id", "access_requests", ["document_id"])
        op.create_index("ix_access_requests_status", "access_requests", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "access_requests"):
        indexes = {index["name"] for index in inspector.get_indexes("access_requests")}
        if "ix_access_requests_status" in indexes:
            op.drop_index("ix_access_requests_status", table_name="access_requests")
        if "ix_access_requests_document_id" in indexes:
            op.drop_index("ix_access_requests_document_id", table_name="access_requests")
        if "ix_access_requests_user_id" in indexes:
            op.drop_index("ix_access_requests_user_id", table_name="access_requests")
        op.drop_table("access_requests")

    if _table_exists(inspector, "document_access_grants"):
        indexes = {index["name"] for index in inspector.get_indexes("document_access_grants")}
        if "ix_document_access_grants_document_id" in indexes:
            op.drop_index("ix_document_access_grants_document_id", table_name="document_access_grants")
        if "ix_document_access_grants_user_id" in indexes:
            op.drop_index("ix_document_access_grants_user_id", table_name="document_access_grants")
        op.drop_table("document_access_grants")

    document_columns = {column["name"] for column in inspector.get_columns("documents")}
    for column_name in [
        "document_status",
        "is_public",
        "security_level",
        "min_permission_level",
        "allowed_departments",
        "visibility_type",
    ]:
        if column_name in document_columns:
            op.drop_column("documents", column_name)
