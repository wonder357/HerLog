"""Allow optional body-fat measurements on existing weight records."""

import sqlalchemy as sa
from alembic import op

revision = "herlog_20261120_body_fat"
down_revision = "herlog_20261120_verify_phone"
branch_labels = None
depends_on = None

TABLE = "qwhealth_herlog_weight"
CHECK = "ck_herlog_weight_body_fat"


def upgrade() -> None:
    if op.get_context().dialect.name == "sqlite":
        op.add_column(TABLE, sa.Column(
            "body_fat_pct", sa.Numeric(5, 2), sa.CheckConstraint("body_fat_pct > 0 AND body_fat_pct < 100", name=CHECK),
        ))
    else:
        op.add_column(TABLE, sa.Column("body_fat_pct", sa.Numeric(5, 2)))
        op.create_check_constraint(CHECK, TABLE, "body_fat_pct > 0 AND body_fat_pct < 100")


def downgrade() -> None:
    if op.get_context().dialect.name != "sqlite":
        op.drop_constraint(CHECK, TABLE, type_="check")
    op.drop_column(TABLE, "body_fat_pct")
