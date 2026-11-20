from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.herlog import _MOMENT, _ROW_ID

CONVERSATIONS = "qwhealth_herlog_assistant_chat"
TURNS = "qwhealth_herlog_assistant_turn"


class AssistantConversation(Base):
    __tablename__ = CONVERSATIONS

    id: Mapped[str] = mapped_column(sa.String(32), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        sa.String(32), sa.ForeignKey("qwhealth_member_auth.customer_id"), nullable=False,
    )
    title: Mapped[str] = mapped_column(sa.String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(_MOMENT)
    __table_args__ = (sa.Index("ix_herlog_assistant_history", "customer_id", "deleted_at", "updated_at", "id"),)


class AssistantTurn(Base):
    __tablename__ = TURNS

    id: Mapped[int] = mapped_column(_ROW_ID, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        sa.String(32), sa.ForeignKey(f"{CONVERSATIONS}.id", ondelete="CASCADE"), nullable=False,
    )
    client_turn_id: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    attempt_id: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    question: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    mode: Mapped[str] = mapped_column(sa.String(8), nullable=False)
    topic: Mapped[str | None] = mapped_column(sa.String(8))
    status: Mapped[str] = mapped_column(sa.String(9), nullable=False)
    source: Mapped[str | None] = mapped_column(sa.String(8))
    answer: Mapped[dict | None] = mapped_column(sa.JSON(none_as_null=True))
    partial: Mapped[str | None] = mapped_column(sa.Text)
    error: Mapped[str | None] = mapped_column(sa.String(200))
    __table_args__ = (
        sa.UniqueConstraint("conversation_id", "client_turn_id", name="uq_herlog_assistant_client_turn"),
        sa.Index("ix_herlog_assistant_turn_order", "conversation_id", "id"),
    )
