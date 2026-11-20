from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

PROFILE_TABLE = "qwhealth_herlog_profile"
PERIOD_TABLE = "qwhealth_herlog_period"
FEELING_TABLE = "qwhealth_herlog_feeling"
WEIGHT_TABLE = "qwhealth_herlog_weight"
SKIN_TABLE = "qwhealth_herlog_skin"
GOAL_TABLE = "qwhealth_herlog_weight_goal"
MEAL_TABLE = "qwhealth_herlog_meal"
POST_TABLE = "qwhealth_herlog_weight_post"

# 生产库是 MySQL，测试库是 SQLite：类型按方言取变体，避免两套模型。
_ROW_ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
_MOMENT = sa.DateTime().with_variant(mysql.DATETIME(fsp=3), "mysql")
_USERNAME = sa.String(32).with_variant(mysql.VARCHAR(32, collation="utf8mb4_bin"), "mysql")


class Profile(Base):
    __tablename__ = PROFILE_TABLE

    customer_id: Mapped[str] = mapped_column(
        sa.String(32), sa.ForeignKey("qwhealth_member_auth.customer_id"), primary_key=True
    )
    username: Mapped[str] = mapped_column(_USERNAME, unique=True, nullable=False)
    birthday: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    height_cm: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 2), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)

    __table_args__ = (
        sa.CheckConstraint("height_cm IS NULL OR height_cm > 0", name="ck_herlog_height"),
    )


class Period(Base):
    __tablename__ = PERIOD_TABLE

    id: Mapped[int] = mapped_column(_ROW_ID, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(
        sa.String(32), sa.ForeignKey("qwhealth_member_auth.customer_id"), nullable=False
    )
    start_day: Mapped[date] = mapped_column(sa.Date, nullable=False)
    end_day: Mapped[date | None] = mapped_column(sa.Date, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("customer_id", "start_day", name="uq_herlog_period_start"),
        sa.CheckConstraint("end_day IS NULL OR end_day >= start_day", name="ck_herlog_period_order"),
    )


class Feeling(Base):
    __tablename__ = FEELING_TABLE

    customer_id: Mapped[str] = mapped_column(
        sa.String(32), sa.ForeignKey("qwhealth_member_auth.customer_id"), primary_key=True
    )
    day: Mapped[date] = mapped_column(sa.Date, primary_key=True)
    flow: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    mood: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    symptoms: Mapped[list[str]] = mapped_column(sa.JSON, nullable=False, default=list)
    impact: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)


class Weight(Base):
    __tablename__ = WEIGHT_TABLE

    id: Mapped[int] = mapped_column(_ROW_ID, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(
        sa.String(32), sa.ForeignKey("qwhealth_member_auth.customer_id"), nullable=False
    )
    client_key: Mapped[str] = mapped_column(sa.String(36), nullable=False)
    grams: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    measured_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)
    tag: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    note: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    feeling_tags: Mapped[list[str] | None] = mapped_column(sa.JSON, nullable=True)
    # 体脂率由家用体脂秤或手动填写，与体重同一笔记录保存，用于体成分趋势。
    body_fat_pct: Mapped[Decimal | None] = mapped_column(sa.Numeric(4, 1), nullable=True)
    source: Mapped[str] = mapped_column(sa.String(12), nullable=False, server_default="manual")
    device_id: Mapped[int | None] = mapped_column(_ROW_ID, nullable=True)
    source_record_id: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("customer_id", "client_key", name="uq_herlog_weight_key"),
        sa.UniqueConstraint("customer_id", "device_id", "source_record_id", name="uq_herlog_weight_source"),
        sa.CheckConstraint("grams > 0", name="ck_herlog_positive_weight"),
        sa.CheckConstraint(
            "body_fat_pct IS NULL OR (body_fat_pct > 0 AND body_fat_pct < 75)",
            name="ck_herlog_body_fat_range",
        ),
        sa.Index("ix_herlog_weight_time", "customer_id", "measured_at", "id"),
    )


class SkinObservation(Base):
    __tablename__ = SKIN_TABLE

    id: Mapped[int] = mapped_column(_ROW_ID, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(
        sa.String(32), sa.ForeignKey("qwhealth_member_auth.customer_id"), nullable=False
    )
    analysis_id: Mapped[str] = mapped_column(sa.String(36), nullable=False)
    site: Mapped[str] = mapped_column(sa.String(40), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)
    mime: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    image_bytes: Mapped[bytes] = mapped_column(
        sa.LargeBinary().with_variant(mysql.MEDIUMBLOB(), "mysql"), nullable=False
    )
    visible: Mapped[str] = mapped_column(sa.Text, nullable=False)
    unclear: Mapped[str] = mapped_column(sa.Text, nullable=False)
    attention: Mapped[str] = mapped_column(sa.Text, nullable=False)
    model_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(sa.String(32), nullable=False)

    __table_args__ = (
        sa.UniqueConstraint("customer_id", "analysis_id", name="uq_herlog_skin_analysis"),
        sa.Index("ix_herlog_skin_time", "customer_id", "captured_at", "id"),
    )


class WeightGoal(Base):
    """会员当前生效的一条减重/维持目标；改目标就是覆盖这一行。"""

    __tablename__ = GOAL_TABLE

    customer_id: Mapped[str] = mapped_column(
        sa.String(32), sa.ForeignKey("qwhealth_member_auth.customer_id"), primary_key=True
    )
    target_grams: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    start_grams: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    start_day: Mapped[date] = mapped_column(sa.Date, nullable=False)
    weekly_rate_grams: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)

    __table_args__ = (
        sa.CheckConstraint("target_grams > 0", name="ck_herlog_goal_target"),
        sa.CheckConstraint("start_grams > 0", name="ck_herlog_goal_start"),
        sa.CheckConstraint("weekly_rate_grams > 0", name="ck_herlog_goal_rate"),
    )


class Meal(Base):
    """一餐的文字记录与热量估算；估算值由服务端写入，用户不能直接改数字。"""

    __tablename__ = MEAL_TABLE

    id: Mapped[int] = mapped_column(_ROW_ID, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(
        sa.String(32), sa.ForeignKey("qwhealth_member_auth.customer_id"), nullable=False
    )
    client_key: Mapped[str] = mapped_column(sa.String(36), nullable=False)
    eaten_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)
    meal_type: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    text: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    kcal: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    protein_g: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    carb_g: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    fat_g: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    estimate_source: Mapped[str] = mapped_column(sa.String(16), nullable=False)

    __table_args__ = (
        sa.UniqueConstraint("customer_id", "client_key", name="uq_herlog_meal_key"),
        sa.CheckConstraint("kcal >= 0", name="ck_herlog_meal_kcal"),
        sa.Index("ix_herlog_meal_time", "customer_id", "eaten_at", "id"),
    )


class WeightPost(Base):
    """体重 tag 的经验广场：一条帖子对所有会员可见，点赞按会员去重。

    官方种子帖没有作者会员，`customer_id` 因此可空。
    """

    __tablename__ = POST_TABLE

    id: Mapped[int] = mapped_column(_ROW_ID, primary_key=True, autoincrement=True)
    customer_id: Mapped[str | None] = mapped_column(
        sa.String(32), sa.ForeignKey("qwhealth_member_auth.customer_id"), nullable=True
    )
    nickname: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    tag: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    body: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    like_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    liked_by: Mapped[list[str]] = mapped_column(sa.JSON, nullable=False, default=list)
    official: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)

    __table_args__ = (
        sa.CheckConstraint("like_count >= 0", name="ck_herlog_post_likes"),
        sa.Index("ix_herlog_post_time", "created_at", "id"),
    )
