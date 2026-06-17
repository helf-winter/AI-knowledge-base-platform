"""add employee authentication fields

Revision ID: 0012_employee_auth
Revises: 0011_conversation_trace
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_employee_auth"
down_revision = "0011_conversation_trace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}
    indexes = {index["name"] for index in inspector.get_indexes("users")}

    if "employee_no" not in columns:
        op.add_column("users", sa.Column("employee_no", sa.String(length=64), nullable=True))
        op.execute("UPDATE users SET employee_no = username WHERE employee_no IS NULL")
    if "position" not in columns:
        op.add_column("users", sa.Column("position", sa.String(length=128), nullable=True))
    if "permission_level" not in columns:
        op.add_column("users", sa.Column("permission_level", sa.Integer(), nullable=False, server_default="1"))
    if "initial_password_code" not in columns:
        op.add_column("users", sa.Column("initial_password_code", sa.String(length=32), nullable=True))
    if "is_first_login" not in columns:
        op.add_column("users", sa.Column("is_first_login", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")))
    if "status" not in columns:
        op.add_column("users", sa.Column("status", sa.String(length=32), nullable=False, server_default="active"))

    if "ix_users_employee_no" not in indexes:
        op.create_index("ix_users_employee_no", "users", ["employee_no"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("users")}
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "ix_users_employee_no" in indexes:
        op.drop_index("ix_users_employee_no", table_name="users")
    for column in ["status", "is_first_login", "initial_password_code", "permission_level", "position", "employee_no"]:
        if column in columns:
            op.drop_column("users", column)
