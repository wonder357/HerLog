"""Persist exercise discussion likes and private bookmarks."""

import sqlalchemy as sa
from alembic import op

revision = "herlog_20261120_reactions"
down_revision = "herlog_20261120_photos"
branch_labels = None
depends_on = None

TABLE = "qwhealth_herlog_discussion_reaction"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("share_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                  sa.ForeignKey("qwhealth_herlog_group_share.id"), primary_key=True),
        sa.Column("kind", sa.String(8), primary_key=True),
        sa.Column("customer_id", sa.String(32), sa.ForeignKey("qwhealth_member_auth.customer_id"), primary_key=True),
        sa.CheckConstraint("kind IN ('like', 'save')", name="ck_herlog_discussion_reaction"),
    )
    op.create_index("ix_herlog_discussion_reaction_member", TABLE, ["customer_id", "kind", "share_id"])


def downgrade() -> None:
    op.drop_index("ix_herlog_discussion_reaction_member", table_name=TABLE)
    op.drop_table(TABLE)
