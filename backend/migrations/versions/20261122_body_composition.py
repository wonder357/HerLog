"""Add body-fat percentage to weight records for body-composition trends."""

import sqlalchemy as sa
from alembic import op

revision = "herlog_20261122_body_composition"
down_revision = "herlog_20261121_discussion_social"
branch_labels = None
depends_on = None

WEIGHT = "qwhealth_herlog_weight"
CHECK = "ck_herlog_weight_body_fat"


def upgrade() -> None:
    context = op.get_context()
    if not context.as_sql and any(column["name"] == "body_fat_pct" for column in sa.inspect(op.get_bind()).get_columns(WEIGHT)):
        return
    if context.dialect.name == "sqlite":
        op.add_column(WEIGHT, sa.Column(
            "body_fat_pct", sa.Numeric(5, 2), sa.CheckConstraint("body_fat_pct > 0 AND body_fat_pct < 100", name=CHECK),
        ))
    else:
        op.add_column(WEIGHT, sa.Column("body_fat_pct", sa.Numeric(5, 2)))
        op.create_check_constraint(CHECK, WEIGHT, "body_fat_pct > 0 AND body_fat_pct < 100")


def downgrade() -> None:
    with op.batch_alter_table(WEIGHT) as batch:
        batch.drop_constraint(CHECK, type_="check")
        batch.drop_column("body_fat_pct")
