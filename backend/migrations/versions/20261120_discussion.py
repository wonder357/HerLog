"""Add public exercise discussion replies and reports."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "herlog_20261120_discussion"
down_revision = "herlog_20261119_home"
branch_labels = None
depends_on = None

REPLY = "qwhealth_herlog_discussion_reply"
REPORT = "qwhealth_herlog_discussion_reply_report"
MEMBER = "qwhealth_member_auth.customer_id"
SHARE = "qwhealth_herlog_group_share.id"


def upgrade() -> None:
    row_id = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    moment = sa.DateTime().with_variant(mysql.DATETIME(fsp=3), "mysql")
    op.create_table(
        REPLY,
        sa.Column("id", row_id, primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(32), unique=True, nullable=False),
        sa.Column("share_id", row_id, sa.ForeignKey(SHARE), nullable=False),
        sa.Column("customer_id", sa.String(32), sa.ForeignKey(MEMBER), nullable=False),
        sa.Column("client_key", sa.String(36), nullable=False),
        sa.Column("body", sa.String(300), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("published_at", moment, nullable=False),
        sa.UniqueConstraint("share_id", "customer_id", "client_key", name="uq_herlog_discussion_reply_key"),
    )
    op.create_index("ix_herlog_discussion_replies", REPLY, ["share_id", "status", "id"])
    op.create_table(
        REPORT,
        sa.Column("reply_id", row_id, sa.ForeignKey(f"{REPLY}.id"), primary_key=True),
        sa.Column("customer_id", sa.String(32), sa.ForeignKey(MEMBER), primary_key=True),
        sa.Column("reason_code", sa.String(20), nullable=False),
        sa.Column("created_at", moment, nullable=False),
    )


def downgrade() -> None:
    op.drop_table(REPORT)
    op.drop_table(REPLY)
