"""Add cycle display preferences and private fertility observations."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "herlog_20261119_fertility"
down_revision = "herlog_20261119_period_mood"
branch_labels = None
depends_on = None


def upgrade() -> None:
    moment = sa.DateTime().with_variant(mysql.DATETIME(fsp=3), "mysql")
    row_id = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table(
        "qwhealth_herlog_cycle_preference",
        sa.Column("customer_id", sa.String(32), sa.ForeignKey("qwhealth_member_auth.customer_id"), primary_key=True),
        sa.Column("active_mode", sa.String(24), nullable=False, server_default="period"),
        sa.Column("seen_fertility", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("trying_started_on", sa.Date()),
    )
    op.create_table(
        "qwhealth_herlog_fertility_daily",
        sa.Column("customer_id", sa.String(32), sa.ForeignKey("qwhealth_member_auth.customer_id"), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("bbt_c", sa.Numeric(4, 2)),
        sa.Column("bbt_measured_at", moment),
        sa.Column("cervical_mucus", sa.String(20)),
        sa.Column("intercourse_occurred", sa.Boolean()),
        sa.Column("revision", sa.String(36), nullable=False),
        sa.Column("updated_at", moment, nullable=False),
    )
    op.create_table(
        "qwhealth_herlog_fertility_test",
        sa.Column("id", row_id, primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.String(32), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("measured_at", moment),
        sa.Column("result", sa.String(20), nullable=False),
        sa.ForeignKeyConstraint(
            ["customer_id", "day"], ["qwhealth_herlog_fertility_daily.customer_id", "qwhealth_herlog_fertility_daily.day"],
            name="fk_herlog_fertility_test_daily", ondelete="CASCADE",
        ),
        sa.UniqueConstraint("customer_id", "day", "measured_at", name="uq_herlog_fertility_test_time"),
    )


def downgrade() -> None:
    op.drop_table("qwhealth_herlog_fertility_test")
    op.drop_table("qwhealth_herlog_fertility_daily")
    op.drop_table("qwhealth_herlog_cycle_preference")
