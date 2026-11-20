"""Add discussion visibility, likes and post images."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "herlog_20261121_discussion_social"
down_revision = "herlog_20261121_assistant"
branch_labels = None
depends_on = None

REPLY = "qwhealth_herlog_discussion_reply"
SHARE = "qwhealth_herlog_group_share"
MEMBER = "qwhealth_member_auth.customer_id"
LIKE = "qwhealth_herlog_discussion_like"
REPLY_LIKE = "qwhealth_herlog_discussion_reply_like"
IMAGE = "qwhealth_herlog_discussion_image"


def upgrade() -> None:
    row_id = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    moment = sa.DateTime().with_variant(mysql.DATETIME(fsp=3), "mysql")
    # 旧回复没有可见性字段，按匿名处理（NULL = 匿名）。
    op.add_column(REPLY, sa.Column("visibility", sa.String(12), nullable=True))
    op.add_column(REPLY, sa.Column("author", sa.String(32), nullable=True))
    op.create_table(
        LIKE,
        sa.Column("share_id", row_id, sa.ForeignKey(f"{SHARE}.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("customer_id", sa.String(32), sa.ForeignKey(MEMBER), primary_key=True),
        sa.Column("created_at", moment, nullable=False),
    )
    op.create_table(
        REPLY_LIKE,
        sa.Column("reply_id", row_id, sa.ForeignKey(f"{REPLY}.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("customer_id", sa.String(32), sa.ForeignKey(MEMBER), primary_key=True),
        sa.Column("created_at", moment, nullable=False),
    )
    op.create_table(
        IMAGE,
        sa.Column("id", row_id, primary_key=True, autoincrement=True),
        sa.Column("share_id", row_id, sa.ForeignKey(f"{SHARE}.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("image_bytes", sa.LargeBinary().with_variant(mysql.MEDIUMBLOB(), "mysql"), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.UniqueConstraint("share_id", "position", name="uq_herlog_discussion_image"),
    )


def downgrade() -> None:
    op.drop_table(IMAGE)
    op.drop_table(REPLY_LIKE)
    op.drop_table(LIKE)
    op.drop_column(REPLY, "author")
    op.drop_column(REPLY, "visibility")
