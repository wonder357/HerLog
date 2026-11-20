"""Add a verified login identity separate from the profile contact phone."""

import sqlalchemy as sa
from alembic import op

revision = "herlog_20261120_verify_phone"
down_revision = "herlog_20261120_reactions"
branch_labels = None
depends_on = None

TABLE = "qwhealth_herlog_profile"
INDEX = "ux_herlog_verified_phone"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("verified_phone", sa.String(11), nullable=True))
    op.create_index(INDEX, TABLE, ["verified_phone"], unique=True)


def downgrade() -> None:
    op.drop_index(INDEX, table_name=TABLE)
    op.drop_column(TABLE, "verified_phone")
