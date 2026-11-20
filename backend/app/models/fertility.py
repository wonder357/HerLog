from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

PREFERENCE_TABLE = "qwhealth_herlog_cycle_preference"
DAILY_TABLE = "qwhealth_herlog_fertility_daily"
TEST_TABLE = "qwhealth_herlog_fertility_test"
MOMENT = sa.DateTime().with_variant(mysql.DATETIME(fsp=3), "mysql")
ROW_ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


class CyclePreference(Base):
    __tablename__ = PREFERENCE_TABLE

    customer_id: Mapped[str] = mapped_column(
        sa.String(32), sa.ForeignKey("qwhealth_member_auth.customer_id"), primary_key=True
    )
    active_mode: Mapped[str] = mapped_column(sa.String(24), nullable=False, server_default="period")
    seen_fertility: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.false())
    trying_started_on: Mapped[date | None] = mapped_column(sa.Date)


class FertilityDaily(Base):
    __tablename__ = DAILY_TABLE

    customer_id: Mapped[str] = mapped_column(
        sa.String(32), sa.ForeignKey("qwhealth_member_auth.customer_id"), primary_key=True
    )
    day: Mapped[date] = mapped_column(sa.Date, primary_key=True)
    bbt_c: Mapped[Decimal | None] = mapped_column(sa.Numeric(4, 2))
    bbt_measured_at: Mapped[datetime | None] = mapped_column(MOMENT)
    cervical_mucus: Mapped[str | None] = mapped_column(sa.String(20))
    intercourse_occurred: Mapped[bool | None] = mapped_column(sa.Boolean)
    revision: Mapped[str] = mapped_column(sa.String(36), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(MOMENT, nullable=False)


class FertilityTest(Base):
    __tablename__ = TEST_TABLE

    id: Mapped[int] = mapped_column(ROW_ID, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    day: Mapped[date] = mapped_column(sa.Date, nullable=False)
    measured_at: Mapped[datetime | None] = mapped_column(MOMENT)
    result: Mapped[str] = mapped_column(sa.String(20), nullable=False)

    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["customer_id", "day"], [f"{DAILY_TABLE}.customer_id", f"{DAILY_TABLE}.day"],
            name="fk_herlog_fertility_test_daily", ondelete="CASCADE",
        ),
        sa.UniqueConstraint("customer_id", "day", "measured_at", name="uq_herlog_fertility_test_time"),
    )
