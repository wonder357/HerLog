"""首页智能体的对话历史。

一问一答在流式回答完成时一次写入两条消息；标题取第一个问题，用户可改名。
所有读写都带 `customer_id` 条件，避免越权读到别人的对话。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.errors import invalid, not_found
from app.models.assistant import AssistantChat, AssistantMessage
from app.schemas.assistant_chat import ChatDetailOut, ChatMessageOut, ChatSummaryOut, detail_out, summary_out

TITLE_MAX = 24
LIST_LIMIT = 50


def title_from(question: str) -> str:
    """用第一个问题做标题：去掉多余空白，过长截断。"""

    condensed = " ".join(question.split())
    if not condensed:
        return "新的对话"
    return condensed if len(condensed) <= TITLE_MAX else condensed[:TITLE_MAX] + "…"


def create_chat(session: Session, customer_id: str, title: str | None = None) -> AssistantChat:
    now = utc_now()
    chat = AssistantChat(
        customer_id=customer_id,
        title=title_from(title) if title else "新的对话",
        created_at=now,
        updated_at=now,
    )
    session.add(chat)
    session.flush()
    return chat


def get_chat(session: Session, customer_id: str, chat_id: int) -> AssistantChat:
    chat = session.scalar(
        select(AssistantChat).where(
            AssistantChat.id == chat_id, AssistantChat.customer_id == customer_id
        )
    )
    if chat is None:
        raise not_found("这段对话不存在")
    return chat


def list_chats(session: Session, customer_id: str, limit: int = LIST_LIMIT) -> list[ChatSummaryOut]:
    rows = session.execute(
        select(AssistantChat)
        .where(AssistantChat.customer_id == customer_id)
        .order_by(AssistantChat.updated_at.desc(), AssistantChat.id.desc())
        .limit(limit)
    ).scalars()
    counters = dict(
        session.execute(
            select(AssistantMessage.chat_id, func.count(AssistantMessage.id))
            .where(AssistantMessage.customer_id == customer_id)
            .group_by(AssistantMessage.chat_id)
        ).all()
    )
    return [
        summary_out(
            chat_id=chat.id,
            title=chat.title,
            message_count=int(counters.get(chat.id, 0)),
            updated_at=chat.updated_at,
        )
        for chat in rows
    ]


def message_count(session: Session, customer_id: str, chat_id: int) -> int:
    total = session.scalar(
        select(func.count(AssistantMessage.id)).where(
            AssistantMessage.chat_id == chat_id, AssistantMessage.customer_id == customer_id
        )
    )
    return int(total or 0)


def chat_detail(session: Session, customer_id: str, chat_id: int) -> ChatDetailOut:
    chat = get_chat(session, customer_id, chat_id)
    messages = session.scalars(
        select(AssistantMessage)
        .where(AssistantMessage.chat_id == chat.id, AssistantMessage.customer_id == customer_id)
        .order_by(AssistantMessage.id)
    )
    return detail_out(
        chat_id=chat.id,
        title=chat.title,
        updated_at=chat.updated_at,
        messages=[
            ChatMessageOut(role=item.role, content=item.content, source=item.source)
            for item in messages
        ],
    )


def rename_chat(session: Session, customer_id: str, chat_id: int, title: str) -> AssistantChat:
    condensed = " ".join(title.split())
    if not condensed:
        raise invalid("标题不能为空")
    if len(condensed) > 60:
        raise invalid("标题最多 60 个字")
    chat = get_chat(session, customer_id, chat_id)
    chat.title = condensed
    chat.updated_at = utc_now()
    session.flush()
    return chat


def delete_chat(session: Session, customer_id: str, chat_id: int) -> None:
    chat = get_chat(session, customer_id, chat_id)
    session.execute(
        delete(AssistantMessage).where(
            AssistantMessage.chat_id == chat.id, AssistantMessage.customer_id == customer_id
        )
    )
    session.delete(chat)
    session.flush()


def append_exchange(
    session: Session,
    customer_id: str,
    question: str,
    answer: str,
    source: str,
    chat_id: int | None = None,
) -> AssistantChat:
    """把一问一答追加到对话；`chat_id` 为空时新建一段对话。"""

    chat = (
        get_chat(session, customer_id, chat_id) if chat_id is not None else create_chat(session, customer_id)
    )
    now: datetime = utc_now()
    if chat.title == "新的对话":
        chat.title = title_from(question)
    session.add_all(
        [
            AssistantMessage(
                chat_id=chat.id,
                customer_id=customer_id,
                role="user",
                content=question,
                source=None,
                created_at=now,
            ),
            AssistantMessage(
                chat_id=chat.id,
                customer_id=customer_id,
                role="assistant",
                content=answer,
                source=source,
                created_at=now,
            ),
        ]
    )
    chat.updated_at = now
    session.flush()
    return chat
