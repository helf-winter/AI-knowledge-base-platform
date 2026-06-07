"""add skills_json to expert_agent_profiles

Revision ID: 0009_add_skills_json_to_expert_agent_profiles
Revises: 0008_add_cluster_key_to_knowledge_gaps
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_add_skills_json_to_expert_agent_profiles"
down_revision = "0008_add_cluster_key_to_knowledge_gaps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("expert_agent_profiles", sa.Column("skills_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("expert_agent_profiles", "skills_json")
