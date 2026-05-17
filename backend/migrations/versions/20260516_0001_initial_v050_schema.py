"""initial v0.5.0 schema — users, sessions, analyses, analysis_runs, narratives

Revision ID: 20260516_0001
Revises:
Create Date: 2026-05-16 12:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260516_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("github_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("github_login", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_users_github_login", "users", ["github_login"])

    op.create_table(
        "sessions",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("access_token_ct", sa.LargeBinary(), nullable=False),
        sa.Column("access_token_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_sessions_user_id", "sessions", ["user_id"])
    op.create_index("idx_sessions_expires_at", "sessions", ["expires_at"])

    op.create_table(
        "analyses",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_login", sa.Text(), nullable=False),
        sa.Column("target_github_id", sa.BigInteger(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("share_slug", sa.Text(), unique=True, nullable=True),
        sa.Column("latest_run_id", sa.BigInteger(), nullable=True),  # FK added below
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "target_login", name="uq_analyses_user_target"),
    )
    op.create_index("idx_analyses_user_id", "analyses", ["user_id"])
    op.create_index("idx_analyses_target_login", "analyses", ["target_login"])

    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.BigInteger(),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("report_json", postgresql.JSONB(), nullable=False),
        sa.Column("total_score", sa.SmallInteger(), nullable=False),
        sa.Column("tier_name", sa.Text(), nullable=False),
        sa.Column("scores_hash", sa.Text(), nullable=False),
        sa.Column("ingestion_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingestion_completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingestion_latency_ms", sa.Integer(), nullable=False),
    )
    op.create_index("idx_runs_analysis_id", "analysis_runs", ["analysis_id"])
    op.create_index(
        "idx_runs_analysis_completed",
        "analysis_runs",
        ["analysis_id", "ingestion_completed_at"],
    )

    # Use the same constraint name the SQLAlchemy model declares.
    op.create_foreign_key(
        "fk_analyses_latest_run_id",
        "analyses",
        "analysis_runs",
        ["latest_run_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "narratives",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "analysis_run_id",
            sa.BigInteger(),
            sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("is_fallback", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "mode IN ('roast','mentor','recruiter','cto','career')",
            name="ck_narratives_mode",
        ),
        sa.UniqueConstraint("analysis_run_id", "mode", name="uq_narratives_run_mode"),
    )
    op.create_index("idx_narratives_run_id", "narratives", ["analysis_run_id"])


def downgrade() -> None:
    op.drop_index("idx_narratives_run_id", table_name="narratives")
    op.drop_table("narratives")
    op.drop_constraint("fk_analyses_latest_run_id", "analyses", type_="foreignkey")
    op.drop_index("idx_runs_analysis_completed", table_name="analysis_runs")
    op.drop_index("idx_runs_analysis_id", table_name="analysis_runs")
    op.drop_table("analysis_runs")
    op.drop_index("idx_analyses_target_login", table_name="analyses")
    op.drop_index("idx_analyses_user_id", table_name="analyses")
    op.drop_table("analyses")
    op.drop_index("idx_sessions_expires_at", table_name="sessions")
    op.drop_index("idx_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("idx_users_github_login", table_name="users")
    op.drop_table("users")
