from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timezone
from uuid import uuid4

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.errors import conflict, not_found
from app.models.assistant import AssistantConversation, AssistantTurn
from app.models.home import HomePreference
from app.schemas.assistant import ConversationOut, TurnOut
from app.schemas.herlog import AssistantExchange, AssistantStreamIn
from app.services.home_service import update_preferences
from app.services.period_service import lock_member


def title_for(question: str, mode: str) -> str:
    topics = (
        (r"经期|月经|周期", "经期记录回顾"),
        (r"护肤|皮肤|防晒", "日常护肤记录"),
        (r"睡眠|睡觉|作息", "关于睡眠记录"),
        (r"运动|散步|健身|跑步", "关于运动记录"),
        (r"体重|称重|体脂|BMI", "体重记录回顾"),
    )
    return next((title for pattern, title in topics if re.search(pattern, question, re.IGNORECASE)),
                "健康记录查询" if mode == "records" else "日常健康对话")


def preference(session: Session, customer_id: str) -> bool | None:
    row = session.get(HomePreference, customer_id)
    return row.assistant_history_enabled if row else None


def set_preference(session: Session, customer_id: str, enabled: bool) -> None:
    update_preferences(session, customer_id, {"assistant_history_enabled": enabled})


def _out(row: AssistantConversation) -> ConversationOut:
    return ConversationOut(id=row.id, title=row.title, updated_at=row.updated_at.replace(tzinfo=timezone.utc).isoformat())


def _owned(session: Session, customer_id: str, conversation_id: str, *, lock: bool = False) -> AssistantConversation:
    query = select(AssistantConversation).where(
        AssistantConversation.id == conversation_id, AssistantConversation.customer_id == customer_id,
        AssistantConversation.deleted_at.is_(None),
    )
    row = session.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise not_found("对话不存在")
    return row


def list_conversations(session: Session, customer_id: str, cursor: str | None, q: str = "") -> dict:
    query = select(AssistantConversation).where(
        AssistantConversation.customer_id == customer_id, AssistantConversation.deleted_at.is_(None),
    )
    if q.strip():
        query = query.where(AssistantConversation.title.icontains(q.strip(), autoescape=True))
    if cursor:
        anchor = session.scalar(select(AssistantConversation).where(
            AssistantConversation.customer_id == customer_id, AssistantConversation.id == cursor,
        ))
        if anchor is None:
            raise not_found("对话不存在")
        query = query.where(or_(
            AssistantConversation.updated_at < anchor.updated_at,
            and_(AssistantConversation.updated_at == anchor.updated_at, AssistantConversation.id < anchor.id),
        ))
    page = list(session.scalars(query.order_by(AssistantConversation.updated_at.desc(), AssistantConversation.id.desc()).limit(21)))
    return {"items": [_out(row) for row in page[:20]], "next_cursor": page[19].id if len(page) > 20 else None}


def detail(session: Session, customer_id: str, conversation_id: str) -> dict:
    row = _owned(session, customer_id, conversation_id)
    turns = session.scalars(select(AssistantTurn).where(AssistantTurn.conversation_id == row.id).order_by(AssistantTurn.id))
    return {"conversation": _out(row), "turns": [
        TurnOut(id=turn.client_turn_id, question=turn.question, mode=turn.mode, topic=turn.topic, status=turn.status,
                source=turn.source, answer=turn.answer, partial=turn.partial, error=turn.error)
        for turn in turns
    ]}


def rename(session: Session, customer_id: str, conversation_id: str, title: str) -> ConversationOut:
    row = _owned(session, customer_id, conversation_id, lock=True)
    row.title = title
    session.commit()
    return _out(row)


def remove(session: Session, customer_id: str, conversation_id: str) -> None:
    row = _owned(session, customer_id, conversation_id, lock=True)
    session.execute(delete(AssistantTurn).where(AssistantTurn.conversation_id == row.id))
    # Keep only the key and owner so a late retry cannot recreate a deleted chat.
    row.title = ""
    row.deleted_at = utc_now()
    session.commit()


@dataclass(frozen=True)
class SavedAttempt:
    conversation: ConversationOut
    turn_id: int
    attempt_id: str
    payload: AssistantStreamIn
    cached_answer: dict | None = None
    cached_source: str | None = None


def begin(session: Session, customer_id: str, payload: AssistantStreamIn) -> SavedAttempt:
    lock_member(session, customer_id)
    conversation = session.scalar(select(AssistantConversation).where(
        AssistantConversation.id == payload.conversation_id,
    ).with_for_update())
    if conversation is not None and (conversation.customer_id != customer_id or conversation.deleted_at):
        raise not_found("对话不存在")
    if preference(session, customer_id) is not True:
        raise conflict("当前已关闭保存历史，可关闭本轮保存后重试")
    now = utc_now()
    if conversation is None:
        if not payload.create_conversation:
            raise not_found("对话不存在")
        conversation = AssistantConversation(
            id=payload.conversation_id, customer_id=customer_id, title=title_for(payload.question, payload.mode),
            created_at=now, updated_at=now,
        )
        session.add(conversation)
        session.flush()
    turn = session.scalar(select(AssistantTurn).where(
        AssistantTurn.conversation_id == conversation.id, AssistantTurn.client_turn_id == payload.client_turn_id,
    ).with_for_update())
    topic = payload.follow_up_topic if payload.mode == "records" else None
    if turn is not None:
        if (turn.question, turn.mode, turn.topic) != (payload.question, payload.mode, topic):
            raise conflict("这条请求已用于其他消息")
        if turn.status == "complete":
            return SavedAttempt(_out(conversation), turn.id, turn.attempt_id, payload, turn.answer, turn.source)
    else:
        turn = AssistantTurn(
            conversation_id=conversation.id, client_turn_id=payload.client_turn_id, question=payload.question,
            mode=payload.mode, topic=topic,
        )
        session.add(turn)
    turn.attempt_id = uuid4().hex
    turn.status = "pending"
    turn.source = turn.partial = turn.error = None
    conversation.updated_at = now
    session.flush()
    if payload.mode == "general":
        previous = list(session.scalars(select(AssistantTurn).where(
            AssistantTurn.conversation_id == conversation.id, AssistantTurn.id < turn.id,
            AssistantTurn.mode == "general", AssistantTurn.status == "complete",
        ).order_by(AssistantTurn.id.desc()).limit(3)))
        from_history = [AssistantExchange(question=row.question, answer=row.answer["answer"][:4000])
                        for row in reversed(previous)]
        payload = payload.model_copy(update={"history": from_history})
    result = SavedAttempt(_out(conversation), turn.id, turn.attempt_id, payload)
    session.commit()
    return result


def finalize(factory, attempt: SavedAttempt, status: str, **fields) -> bool:
    with factory.begin() as session:
        result = session.execute(update(AssistantTurn).where(
            AssistantTurn.id == attempt.turn_id, AssistantTurn.attempt_id == attempt.attempt_id,
            AssistantTurn.status == "pending",
        ).values(status=status, **fields))
        return result.rowcount == 1
