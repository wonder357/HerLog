"""Add body-fat percentage to weight records for body-composition trends."""

import sqlalchemy as sa
from alembic import op

revision = "herlog_20261122_body_composition"
down_revision = "herlog_20261121_discussion_social"
branch_labels = None
depends_on = None

WEIGHT = "qwhealth_herlog_weight"
CHECK = "ck_herlog_body_fat_range"


def upgrade() -> None:
    # 体脂率允许为空：只有体脂秤或用户手动填写时才有值，不影响体重本身的记录。
    with op.batch_alter_table(WEIGHT) as batch:
        batch.add_column(sa.Column("body_fat_pct", sa.Numeric(4, 1), nullable=True))
        batch.create_check_constraint(
            CHECK, "body_fat_pct IS NULL OR (body_fat_pct > 0 AND body_fat_pct < 75)"
        )


def downgrade() -> None:
    with op.batch_alter_table(WEIGHT) as batch:
        batch.drop_constraint(CHECK, type_="check")
        batch.drop_column("body_fat_pct")
