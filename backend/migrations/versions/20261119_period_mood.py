"""Add an optional mood to the daily feeling journal."""

import sqlalchemy as sa
from alembic import op

revision = "herlog_20261119_period_mood"
down_revision = "herlog_20261119_wellness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("qwhealth_herlog_feeling", sa.Column("mood", sa.String(16), nullable=True))


def downgrade() -> None:
    op.drop_column("qwhealth_herlog_feeling", "mood")
