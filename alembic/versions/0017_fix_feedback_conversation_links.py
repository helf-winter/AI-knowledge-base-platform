"""remove obsolete feedback foreign keys

Revision ID: 0017_fix_feedback_links
Revises: 0016_learning_gap_drafts
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa


revision = "0017_fix_feedback_links"
down_revision = "0016_learning_gap_drafts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "feedbacks" not in inspector.get_table_names():
        return

    for foreign_key in inspector.get_foreign_keys("feedbacks"):
        if foreign_key.get("referred_table") in {"answers", "sessions"} and foreign_key.get("name"):
            op.drop_constraint(foreign_key["name"], "feedbacks", type_="foreignkey")


def downgrade() -> None:
    # Current feedback IDs refer to conversation_turns. Restoring the obsolete
    # answers/sessions constraints would reject valid data created after upgrade.
    pass

