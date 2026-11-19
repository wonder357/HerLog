"""Manual wellness logging and private group sharing."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "herlog_20261119_wellness"
down_revision = "herlog_20261119_weight"
branch_labels = None
depends_on = None

PREFIX = "qwhealth_herlog_"
MEMBER = "qwhealth_member_auth.customer_id"
ROW_ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
MOMENT = sa.DateTime().with_variant(mysql.DATETIME(fsp=3), "mysql")


def member_column(*, primary_key=False):
    return sa.Column("customer_id", sa.String(32), sa.ForeignKey(MEMBER), primary_key=primary_key, nullable=False)


def upgrade():
    op.add_column(PREFIX + "weight", sa.Column("feeling_tags", sa.JSON(), nullable=True))
    op.add_column(PREFIX + "weight", sa.Column("source", sa.String(12), server_default="manual", nullable=False))
    op.add_column(PREFIX + "weight", sa.Column("device_id", ROW_ID, nullable=True))
    op.add_column(PREFIX + "weight", sa.Column("source_record_id", sa.String(128), nullable=True))
    op.create_index("uq_herlog_weight_source", PREFIX + "weight",
                    ["customer_id", "device_id", "source_record_id"], unique=True)
    op.create_table(
        PREFIX + "exercise_checkin",
        sa.Column("id", ROW_ID, primary_key=True, autoincrement=True),
        member_column(),
        sa.Column("client_key", sa.String(36), nullable=False),
        sa.Column("activity_code", sa.String(20), nullable=False),
        sa.Column("started_at", MOMENT, nullable=False),
        sa.Column("duration_minutes", sa.Integer()),
        sa.Column("effort", sa.String(16)),
        sa.Column("feeling_code", sa.String(16)),
        sa.UniqueConstraint("customer_id", "client_key", name="uq_herlog_checkin_key"),
    )
    op.create_index("ix_herlog_checkin_time", PREFIX + "exercise_checkin", ["customer_id", "started_at", "id"])
    op.create_table(
        PREFIX + "skin_journal",
        member_column(primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("skin_type", sa.String(12)),
        sa.Column("comfort", sa.Integer()),
        sa.Column("sensations", sa.JSON(), nullable=False),
        sa.Column("routine", sa.JSON(), nullable=False),
        sa.Column("note", sa.String(400)),
        sa.CheckConstraint("comfort BETWEEN 1 AND 5", name="ck_herlog_skin_comfort"),
    )
    op.create_table(
        PREFIX + "group_member",
        member_column(primary_key=True),
        sa.Column("topic", sa.String(12), primary_key=True),
        sa.Column("group_key", sa.String(16), primary_key=True),
        sa.Column("consented_at", MOMENT, nullable=False),
    )
    op.create_table(
        PREFIX + "group_share",
        sa.Column("id", ROW_ID, primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(32), unique=True, nullable=False),
        member_column(),
        sa.Column("topic", sa.String(12), nullable=False),
        sa.Column("group_key", sa.String(16), nullable=False),
        sa.Column("reference_key", sa.String(32), nullable=False),
        sa.Column("client_key", sa.String(36), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("published_at", MOMENT, nullable=False),
        sa.UniqueConstraint("customer_id", "topic", "client_key", name="uq_herlog_share_client_key"),
        sa.UniqueConstraint("customer_id", "topic", "group_key", "reference_key", name="uq_herlog_share_ref"),
    )
    op.create_index("ix_herlog_group_feed", PREFIX + "group_share", ["topic", "group_key", "status", "id"])
    op.create_table(
        PREFIX + "share_report",
        sa.Column("share_id", ROW_ID, sa.ForeignKey(PREFIX + "group_share.id"), primary_key=True),
        member_column(primary_key=True),
        sa.Column("reason_code", sa.String(20), nullable=False),
        sa.Column("created_at", MOMENT, nullable=False),
    )
    op.create_table(
        PREFIX + "group_reply",
        sa.Column("share_id", ROW_ID, sa.ForeignKey(PREFIX + "group_share.id"), primary_key=True),
        member_column(primary_key=True),
        sa.Column("reply_code", sa.String(20), nullable=False),
    )


def downgrade():
    raise RuntimeError("Restore the database snapshot to roll back.")
