"""add evaluation tables

Revision ID: 0003_evaluation_tables
Revises: 0002_pgvector_chunk_embedding
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_evaluation_tables"
down_revision = "0002_add_chunk_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evaluation_cases",
        sa.Column("case_id", sa.String(length=36), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_answer", sa.Text(), nullable=False),
        sa.Column("source_references_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="general"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("run_id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("retriever_version", sa.String(length=32), nullable=False),
        sa.Column("avg_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_cases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "evaluation_results",
        sa.Column("result_id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("evaluation_runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_id", sa.String(length=36), sa.ForeignKey("evaluation_cases.case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("score_recall", sa.Float(), nullable=False),
        sa.Column("score_precision", sa.Float(), nullable=False),
        sa.Column("score_faithfulness", sa.Float(), nullable=False),
        sa.Column("score_groundedness", sa.Float(), nullable=False),
        sa.Column("score_overall", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_evaluation_results_run_id", "evaluation_results", ["run_id"])
    op.create_index("ix_evaluation_results_case_id", "evaluation_results", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_evaluation_results_case_id", table_name="evaluation_results")
    op.drop_index("ix_evaluation_results_run_id", table_name="evaluation_results")
    op.drop_table("evaluation_results")
    op.drop_table("evaluation_runs")
    op.drop_table("evaluation_cases")
