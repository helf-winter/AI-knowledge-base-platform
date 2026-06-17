"""add skills_json to expert_agent_profiles

Revision ID: 0009_agent_skills
Revises: 0008_knowledge_gaps
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_agent_skills"
down_revision = "0008_knowledge_gaps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("expert_agent_profiles"):
        op.create_table(
            "expert_agent_profiles",
            sa.Column("agent_id", sa.String(length=36), primary_key=True),
            sa.Column("agent_name", sa.String(length=128), nullable=False, unique=True),
            sa.Column("domain_name", sa.String(length=128), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("knowledge_scope_json", sa.Text(), nullable=True),
            sa.Column("skills_json", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        )
    else:
        columns = {column["name"] for column in inspector.get_columns("expert_agent_profiles")}
        if "skills_json" not in columns:
            op.add_column("expert_agent_profiles", sa.Column("skills_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("expert_agent_profiles", "skills_json")
