"""体重 tag 扩展：目标、饮食记录、经验广场。

Revision ID: herlog_20261119_weight
Revises: herlog_20261118
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "herlog_20261119_weight"
down_revision = "herlog_20261118"
branch_labels = None
depends_on = None

MEMBER = "qwhealth_member_auth"
GOAL = "qwhealth_herlog_weight_goal"
MEAL = "qwhealth_herlog_meal"
POST = "qwhealth_herlog_weight_post"


def upgrade():
    op.create_table(
        GOAL,
        sa.Column("customer_id", sa.String(32), sa.ForeignKey(f"{MEMBER}.customer_id"),
                  primary_key=True, nullable=False),
        sa.Column("target_grams", sa.Integer(), nullable=False),
        sa.Column("start_grams", sa.Integer(), nullable=False),
        sa.Column("start_day", sa.Date(), nullable=False),
        sa.Column("weekly_rate_grams", sa.Integer(), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=3), nullable=False),
        sa.CheckConstraint("target_grams > 0", name="ck_herlog_goal_target"),
        sa.CheckConstraint("start_grams > 0", name="ck_herlog_goal_start"),
        sa.CheckConstraint("weekly_rate_grams > 0", name="ck_herlog_goal_rate"),
        mysql_charset="utf8mb4",
    )
    op.create_table(
        MEAL,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.String(32), sa.ForeignKey(f"{MEMBER}.customer_id"),
                  nullable=False),
        sa.Column("client_key", sa.String(36), nullable=False),
        sa.Column("eaten_at", mysql.DATETIME(fsp=3), nullable=False),
        sa.Column("meal_type", sa.String(16), nullable=False),
        sa.Column("text", sa.String(500), nullable=False),
        sa.Column("kcal", sa.Integer(), nullable=False),
        sa.Column("protein_g", sa.Integer(), nullable=False),
        sa.Column("carb_g", sa.Integer(), nullable=False),
        sa.Column("fat_g", sa.Integer(), nullable=False),
        sa.Column("estimate_source", sa.String(16), nullable=False),
        sa.UniqueConstraint("customer_id", "client_key", name="uq_herlog_meal_key"),
        sa.CheckConstraint("kcal >= 0", name="ck_herlog_meal_kcal"),
    )
    op.create_index("ix_herlog_meal_time", MEAL, ["customer_id", "eaten_at", "id"])
    op.create_table(
        POST,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.String(32), sa.ForeignKey(f"{MEMBER}.customer_id"),
                  nullable=True),
        sa.Column("nickname", sa.String(32), nullable=False),
        sa.Column("tag", sa.String(16), nullable=False),
        sa.Column("body", sa.String(500), nullable=False),
        sa.Column("like_count", sa.Integer(), nullable=False),
        sa.Column("liked_by", sa.JSON(), nullable=False),
        sa.Column("official", sa.Boolean(), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=3), nullable=False),
        sa.CheckConstraint("like_count >= 0", name="ck_herlog_post_likes"),
    )
    op.create_index("ix_herlog_post_time", POST, ["created_at", "id"])


def downgrade():
    raise RuntimeError("Restore a contest database snapshot to roll back.")
