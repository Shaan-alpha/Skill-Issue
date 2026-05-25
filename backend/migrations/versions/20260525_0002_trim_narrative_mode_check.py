"""trim narrative mode check constraint to ('roast','mentor')

Recruiter / CTO / Career modes were dropped from the product on 2026-05-19
(CHANGELOG v0.6.0). The original v0.5.0 schema's CHECK constraint allowed all
five values; this migration tightens it so the database mirrors the live
contract.

If any rows with a now-disallowed mode exist (none should, but a stale dev DB
could carry them), upgrade will fail loudly. That's intentional — silent data
loss is worse. Operator fix: delete or backfill the offending rows manually,
then re-run upgrade.

Revision ID: 20260525_0002
Revises: 20260516_0001
Create Date: 2026-05-25 12:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "20260525_0002"
down_revision = "20260516_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_narratives_mode", "narratives", type_="check")
    op.create_check_constraint(
        "ck_narratives_mode",
        "narratives",
        "mode IN ('roast','mentor')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_narratives_mode", "narratives", type_="check")
    op.create_check_constraint(
        "ck_narratives_mode",
        "narratives",
        "mode IN ('roast','mentor','recruiter','cto','career')",
    )
