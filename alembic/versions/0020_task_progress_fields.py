"""add task progress fields

Revision ID: 0020_task_progress_fields
Revises: 0019_bge_m3_embeddings
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa


revision = "0020_task_progress_fields"
down_revision = "0019_bge_m3_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "tasks" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("tasks")}
    if "stage" not in columns:
        op.add_column("tasks", sa.Column("stage", sa.String(length=64), nullable=True))
    if "progress_current" not in columns:
        op.add_column("tasks", sa.Column("progress_current", sa.Integer(), nullable=False, server_default="0"))
    if "progress_total" not in columns:
        op.add_column("tasks", sa.Column("progress_total", sa.Integer(), nullable=False, server_default="0"))
    if "detail" not in columns:
        op.add_column("tasks", sa.Column("detail", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "tasks" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("tasks")}
    if "detail" in columns:
        op.drop_column("tasks", "detail")
    if "progress_total" in columns:
        op.drop_column("tasks", "progress_total")
    if "progress_current" in columns:
        op.drop_column("tasks", "progress_current")
    if "stage" in columns:
        op.drop_column("tasks", "stage")
