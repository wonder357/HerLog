"""Women's health contest extension on the verified Qiwen API reference head."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "herlog_20261118"
down_revision = "h9b0c1d2e3f4"
branch_labels = None
depends_on = None

MEMBER = "qwhealth_member_auth"
PROFILE = "qwhealth_herlog_profile"
PERIOD = "qwhealth_herlog_period"
FEELING = "qwhealth_herlog_feeling"
WEIGHT = "qwhealth_herlog_weight"
SKIN = "qwhealth_herlog_skin"


def owner(primary_key=False):
    return sa.Column("customer_id", sa.String(32), sa.ForeignKey(f"{MEMBER}.customer_id"),
                     nullable=False, primary_key=primary_key)


def row_id():
    return sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True)


def upgrade():
    # The pinned baseline ORM reads org_id, but its fresh Alembic chain omits this column.
    op.add_column(MEMBER, sa.Column("org_id", sa.String(32), nullable=True))
    op.alter_column(MEMBER, "phone", existing_type=sa.String(20), nullable=True)
    op.create_table(
        PROFILE, owner(primary_key=True),
        sa.Column("username", sa.String(32, collation="utf8mb4_bin"), nullable=False),
        sa.Column("birthday", sa.Date()), sa.Column("height_cm", sa.Numeric(5, 2)),
        sa.Column("contact_phone", sa.String(32)),
        sa.UniqueConstraint("username", name="uq_herlog_username"),
        sa.CheckConstraint("height_cm IS NULL OR height_cm > 0", name="ck_herlog_height"),
        mysql_charset="utf8mb4",
    )
    op.create_table(
        PERIOD, row_id(), owner(), sa.Column("start_day", sa.Date(), nullable=False),
        sa.Column("end_day", sa.Date()),
        sa.UniqueConstraint("customer_id", "start_day", name="uq_herlog_period_start"),
        sa.CheckConstraint("end_day IS NULL OR end_day >= start_day", name="ck_herlog_period_order"),
    )
    op.create_table(
        FEELING, owner(primary_key=True), sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("flow", sa.String(16)), sa.Column("symptoms", sa.JSON(), nullable=False),
        sa.Column("impact", sa.String(64)), sa.Column("note", sa.String(500)),
    )
    op.create_table(
        WEIGHT, row_id(), owner(), sa.Column("client_key", sa.String(36), nullable=False),
        sa.Column("grams", sa.Integer(), nullable=False),
        sa.Column("measured_at", mysql.DATETIME(fsp=3), nullable=False),
        sa.Column("tag", sa.String(32)), sa.Column("note", sa.String(500)),
        sa.UniqueConstraint("customer_id", "client_key", name="uq_herlog_weight_key"),
        sa.CheckConstraint("grams > 0", name="ck_herlog_positive_weight"),
    )
    op.create_index("ix_herlog_weight_time", WEIGHT, ["customer_id", "measured_at", "id"])
    op.create_table(
        SKIN, row_id(), owner(), sa.Column("analysis_id", sa.String(36), nullable=False),
        sa.Column("site", sa.String(40), nullable=False),
        sa.Column("captured_at", mysql.DATETIME(fsp=3), nullable=False),
        sa.Column("mime", sa.String(32), nullable=False),
        sa.Column("image_bytes", mysql.MEDIUMBLOB(), nullable=False),
        sa.Column("visible", sa.Text(), nullable=False), sa.Column("unclear", sa.Text(), nullable=False),
        sa.Column("attention", sa.Text(), nullable=False), sa.Column("model_id", sa.String(128), nullable=False),
        sa.Column("prompt_version", sa.String(32), nullable=False),
        sa.UniqueConstraint("customer_id", "analysis_id", name="uq_herlog_skin_analysis"),
    )
    op.create_index("ix_herlog_skin_time", SKIN, ["customer_id", "captured_at", "id"])


def downgrade():
    raise RuntimeError("Restore a contest database snapshot to roll back. Username-only accounts may have NULL phone.")

