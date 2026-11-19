"""Add account preferences for the home and profile pages."""

import sqlalchemy as sa
from alembic import op

revision = "herlog_20261119_home"
down_revision = "herlog_20261119_fertility"
branch_labels = None
depends_on = None
TABLE = "qwhealth_herlog_home_preference"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("customer_id", sa.String(32), sa.ForeignKey("qwhealth_member_auth.customer_id"), primary_key=True),
        sa.Column("period_reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("record_reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("weekly_record_days_target", sa.SmallInteger()),
        sa.Column("show_focus", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_summary", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_questions", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("password_attempt_count", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("password_attempt_window", sa.BigInteger()),
    )


def downgrade() -> None:
    op.drop_table(TABLE)
