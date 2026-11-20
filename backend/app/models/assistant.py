from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.herlog import _MOMENT, _ROW_ID

MEMBER = "qwhealth_member_auth.customer_id"
PREFIX = "qwhealth_herlog_"


class AssistantChat(Base):
    """首页智能体的一段对话。标题取第一个问题，用户可改名。"""

    __tablename__ = PREFIX + "assistant_chat"

    id: Mapped[int] = mapped_column(_ROW_ID, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(sa.String(32), sa.ForeignKey(MEMBER), nullable=False)
    title: Mapped[str] = mapped_column(sa.String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)

    __table_args__ = (sa.Index("ix_herlog_assistant_chat_owner", "customer_id", "updated_at", "id"),)


class AssistantMessage(Base):
    """对话里的一问或一答。角色与来源都留痕，历史回看时能标出演示样例。"""

    __tablename__ = PREFIX + "assistant_message"

    id: Mapped[int] = mapped_column(_ROW_ID, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(
        _ROW_ID, sa.ForeignKey(f"{PREFIX}assistant_chat.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[str] = mapped_column(sa.String(32), sa.ForeignKey(MEMBER), nullable=False)
    role: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    source: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(_MOMENT, nullable=False)

    __table_args__ = (
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_herlog_assistant_role"),
        sa.Index("ix_herlog_assistant_message_chat", "chat_id", "id"),
    )
