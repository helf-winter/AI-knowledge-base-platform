"""add batch import tables

Revision ID: 0005_batch_import_tables
Revises: 0004_observability_tables
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_batch_import_tables"
down_revision = "0004_observability_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "batch_import_jobs",
        sa.Column("job_id", sa.String(length=36), primary_key=True),
        sa.Column("job_name", sa.String(length=128), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False, server_default="upload"),
        sa.Column("total_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "batch_import_items",
        sa.Column("item_id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_batch_import_items_job_id", "batch_import_items", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_batch_import_items_job_id", table_name="batch_import_items")
    op.drop_table("batch_import_items")
    op.drop_table("batch_import_jobs")
