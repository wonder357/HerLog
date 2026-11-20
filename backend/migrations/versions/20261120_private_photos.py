"""Add optional private photos for measurements, check-ins and profile."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "herlog_20261120_photos"
down_revision = "herlog_20261120_discussion"
branch_labels = None
depends_on = None

TARGETS = (
    ("qwhealth_herlog_weight_photo", "qwhealth_herlog_weight.id"),
    ("qwhealth_herlog_checkin_photo", "qwhealth_herlog_exercise_checkin.id"),
    ("qwhealth_herlog_profile_photo", "qwhealth_herlog_profile.customer_id"),
)


def upgrade() -> None:
    for name, parent in TARGETS:
        key_type = sa.String(32) if parent.endswith("customer_id") else sa.BigInteger().with_variant(sa.Integer(), "sqlite")
        op.create_table(
            name,
            sa.Column("record_id", key_type, sa.ForeignKey(parent, ondelete="CASCADE"), primary_key=True),
            sa.Column("image_bytes", sa.LargeBinary().with_variant(mysql.MEDIUMBLOB(), "mysql"), nullable=False),
            sa.Column("digest", sa.String(64), nullable=False),
        )


def downgrade() -> None:
    for name, _ in reversed(TARGETS):
        op.drop_table(name)
