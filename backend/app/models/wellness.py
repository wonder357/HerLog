from __future__ import annotations

from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.herlog import _MOMENT, _ROW_ID

MEMBER = "qwhealth_member_auth.customer_id"
PREFIX = "qwhealth_herlog_"


class Checkin(Base):
    __tablename__ = PREFIX + "exercise_checkin"

    id: Mapped[int] = mapped_column(_ROW_ID, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(sa.String(32), sa.ForeignKey(MEMBER), nullable=False)
    client_key: Mapped[str] = mapped_column(sa.String(36), nullable=False)
    activity_code: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(nullable=True)
    effort: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    feeling_code: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("customer_id", "client_key", name="uq_herlog_checkin_key"),
        sa.Index("ix_herlog_checkin_time", "customer_id", "started_at", "id"),
    )


class SkinJournal(Base):
    __tablename__ = PREFIX + "skin_journal"

    customer_id: Mapped[str] = mapped_column(sa.String(32), sa.ForeignKey(MEMBER), primary_key=True)
    day: Mapped[date] = mapped_column(sa.Date, primary_key=True)
    skin_type: Mapped[str | None] = mapped_column(sa.String(12), nullable=True)
    comfort: Mapped[int | None] = mapped_column(nullable=True)
    sensations: Mapped[list[str]] = mapped_column(sa.JSON, nullable=False)
    routine: Mapped[list[str]] = mapped_column(sa.JSON, nullable=False)
    note: Mapped[str | None] = mapped_column(sa.String(400), nullable=True)

    __table_args__ = (sa.CheckConstraint("comfort BETWEEN 1 AND 5", name="ck_herlog_skin_comfort"),)


class GroupMembership(Base):
    __tablename__ = PREFIX + "group_member"

    customer_id: Mapped[str] = mapped_column(sa.String(32), sa.ForeignKey(MEMBER), primary_key=True)
    topic: Mapped[str] = mapped_column(sa.String(12), primary_key=True)
    group_key: Mapped[str] = mapped_column(sa.String(16), primary_key=True)
    consented_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)


class GroupShare(Base):
    __tablename__ = PREFIX + "group_share"

    id: Mapped[int] = mapped_column(_ROW_ID, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(sa.String(32), unique=True, nullable=False)
    customer_id: Mapped[str] = mapped_column(sa.String(32), sa.ForeignKey(MEMBER), nullable=False)
    topic: Mapped[str] = mapped_column(sa.String(12), nullable=False)
    group_key: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    reference_key: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    client_key: Mapped[str] = mapped_column(sa.String(36), nullable=False)
    snapshot: Mapped[dict] = mapped_column(sa.JSON, nullable=False)
    status: Mapped[str] = mapped_column(sa.String(12), nullable=False)
    published_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)

    __table_args__ = (
        sa.UniqueConstraint("customer_id", "topic", "client_key", name="uq_herlog_share_client_key"),
        sa.UniqueConstraint("customer_id", "topic", "group_key", "reference_key", name="uq_herlog_share_ref"),
        sa.Index("ix_herlog_group_feed", "topic", "group_key", "status", "id"),
    )


class ShareReport(Base):
    __tablename__ = PREFIX + "share_report"

    share_id: Mapped[int] = mapped_column(_ROW_ID, sa.ForeignKey(f"{GroupShare.__tablename__}.id"), primary_key=True)
    customer_id: Mapped[str] = mapped_column(sa.String(32), sa.ForeignKey(MEMBER), primary_key=True)
    reason_code: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)


class GroupReply(Base):
    __tablename__ = PREFIX + "group_reply"

    share_id: Mapped[int] = mapped_column(_ROW_ID, sa.ForeignKey(f"{GroupShare.__tablename__}.id"), primary_key=True)
    customer_id: Mapped[str] = mapped_column(sa.String(32), sa.ForeignKey(MEMBER), primary_key=True)
    reply_code: Mapped[str] = mapped_column(sa.String(20), nullable=False)


class DiscussionReply(Base):
    __tablename__ = PREFIX + "discussion_reply"

    id: Mapped[int] = mapped_column(_ROW_ID, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(sa.String(32), unique=True, nullable=False)
    share_id: Mapped[int] = mapped_column(_ROW_ID, sa.ForeignKey(f"{GroupShare.__tablename__}.id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(sa.String(32), sa.ForeignKey(MEMBER), nullable=False)
    client_key: Mapped[str] = mapped_column(sa.String(36), nullable=False)
    body: Mapped[str] = mapped_column(sa.String(300), nullable=False)
    visibility: Mapped[str | None] = mapped_column(sa.String(12), nullable=True)
    author: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    status: Mapped[str] = mapped_column(sa.String(12), nullable=False)
    published_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)

    __table_args__ = (
        sa.UniqueConstraint("share_id", "customer_id", "client_key", name="uq_herlog_discussion_reply_key"),
        sa.Index("ix_herlog_discussion_replies", "share_id", "status", "id"),
    )


class DiscussionLike(Base):
    __tablename__ = PREFIX + "discussion_like"

    share_id: Mapped[int] = mapped_column(
        _ROW_ID, sa.ForeignKey(f"{GroupShare.__tablename__}.id", ondelete="CASCADE"), primary_key=True
    )
    customer_id: Mapped[str] = mapped_column(sa.String(32), sa.ForeignKey(MEMBER), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)


class DiscussionReplyLike(Base):
    __tablename__ = PREFIX + "discussion_reply_like"

    reply_id: Mapped[int] = mapped_column(
        _ROW_ID, sa.ForeignKey(f"{DiscussionReply.__tablename__}.id", ondelete="CASCADE"), primary_key=True
    )
    customer_id: Mapped[str] = mapped_column(sa.String(32), sa.ForeignKey(MEMBER), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)


class DiscussionImage(Base):
    __tablename__ = PREFIX + "discussion_image"

    id: Mapped[int] = mapped_column(_ROW_ID, primary_key=True, autoincrement=True)
    share_id: Mapped[int] = mapped_column(
        _ROW_ID, sa.ForeignKey(f"{GroupShare.__tablename__}.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(nullable=False)
    image_bytes: Mapped[bytes] = mapped_column(
        sa.LargeBinary().with_variant(mysql.MEDIUMBLOB(), "mysql"), nullable=False, deferred=True
    )
    digest: Mapped[str] = mapped_column(sa.String(64), nullable=False)

    __table_args__ = (sa.UniqueConstraint("share_id", "position", name="uq_herlog_discussion_image"),)


class DiscussionReplyReport(Base):
    __tablename__ = PREFIX + "discussion_reply_report"

    reply_id: Mapped[int] = mapped_column(_ROW_ID, sa.ForeignKey(f"{DiscussionReply.__tablename__}.id"), primary_key=True)
    customer_id: Mapped[str] = mapped_column(sa.String(32), sa.ForeignKey(MEMBER), primary_key=True)
    reason_code: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)
