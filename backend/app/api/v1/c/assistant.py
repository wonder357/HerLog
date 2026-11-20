from __future__ import annotations

import logging
from contextlib import aclosing
from typing import Annotated

from anyio import CancelScope
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_current_user, own_account
from app.db.session import get_session
from app.schemas.assistant import ConversationTitleIn, HistoryPreferenceIn
from app.schemas.common import ApiResponse
from app.schemas.herlog import AssistantAnswerOut, AssistantQueryIn, AssistantStreamIn
from app.services import assistant_history, assistant_service, assistant_stream
from app.services.auth_service import CurrentUser

router = APIRouter(prefix="/herlog/assistant", tags=["assistant"], dependencies=[Depends(own_account)])
Db = Annotated[Session, Depends(get_session)]
User = Annotated[CurrentUser, Depends(get_current_user)]
logger = logging.getLogger(__name__)


class HistorySearchIn(BaseModel):
    q: str = Field(max_length=24)
    cursor: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")


@router.get("/history-preference")
def history_preference(db: Db, user: User):
    return ApiResponse(data={"enabled": assistant_history.preference(db, user.customer_id)})


@router.put("/history-preference")
def write_history_preference(payload: HistoryPreferenceIn, db: Db, user: User):
    assistant_history.set_preference(db, user.customer_id, payload.enabled)
    return ApiResponse(data={"enabled": payload.enabled})


@router.get("/conversations")
def list_history(db: Db, user: User, cursor: Annotated[str | None, Query(pattern=r"^[0-9a-f]{32}$")] = None):
    return ApiResponse(data=assistant_history.list_conversations(db, user.customer_id, cursor))


@router.post("/conversations/search")
def search_history(payload: HistorySearchIn, db: Db, user: User):
    return ApiResponse(data=assistant_history.list_conversations(db, user.customer_id, payload.cursor, payload.q))


@router.get("/conversations/{conversation_id}")
def read_history(conversation_id: str, db: Db, user: User):
    return ApiResponse(data=assistant_history.detail(db, user.customer_id, conversation_id))


@router.put("/conversations/{conversation_id}")
def rename_history(conversation_id: str, payload: ConversationTitleIn, db: Db, user: User):
    return ApiResponse(data=assistant_history.rename(db, user.customer_id, conversation_id, payload.title))


@router.delete("/conversations/{conversation_id}")
def delete_history(conversation_id: str, db: Db, user: User):
    assistant_history.remove(db, user.customer_id, conversation_id)
    return ApiResponse(data=None)


@router.post("/query", response_model=ApiResponse[AssistantAnswerOut])
def query(payload: AssistantQueryIn, db: Db, user: User):
    return ApiResponse(data=assistant_service.answer_question(db, user.customer_id, payload.question, payload.follow_up_topic))


async def _stream(payload, record_answer, saved, factory):
    encode = assistant_stream.encode_event
    make_event = assistant_stream.event
    if saved and saved.cached_answer is not None:
        yield encode(make_event("accepted", conversation=saved.conversation.model_dump(mode="json")))
        if saved.cached_source:
            yield encode(make_event("source", source=saved.cached_source))
        yield encode(make_event("complete", answer=saved.cached_answer))
        return
    finished = False
    partial = []
    source = None
    try:
        if saved:
            yield encode(make_event("accepted", conversation=saved.conversation.model_dump(mode="json")))
        async with aclosing(assistant_stream.stream_assistant(payload, record_answer)) as events:
            async for packet in events:
                kind = packet["type"]
                if saved:
                    if kind == "source":
                        source = packet["source"]
                    elif kind == "delta":
                        partial.append(packet["text"])
                    elif kind in {"complete", "error"}:
                        fields = {"source": source}
                        if kind == "complete":
                            status = "complete"
                            fields["answer"] = packet["answer"]
                        else:
                            status = "failed"
                            fields.update(partial="".join(partial) or None, error=packet["message"][:200])
                        updated = await run_in_threadpool(assistant_history.finalize, factory, saved, status, **fields)
                        finished = True
                        if not updated:
                            yield encode(make_event("error", message="对话已更新，请从历史重新打开。"))
                            return
                yield encode(packet)
    except Exception as failure:
        logger.warning("assistant conversation failed: %s", type(failure).__name__)
        yield encode(make_event("error", message="暂时无法完成回答，请重试这条问题。"))
    finally:
        if saved and not finished:
            with CancelScope(shield=True):
                try:
                    await run_in_threadpool(
                        assistant_history.finalize, factory, saved, "stopped",
                        partial="".join(partial) or None, source=source, error="本次回答未完成，可以重试。",
                    )
                except SQLAlchemyError as failure:
                    logger.warning("assistant interruption was not saved: %s", type(failure).__name__)


@router.post("/stream", response_class=StreamingResponse)
def stream(payload: AssistantStreamIn, db: Db, user: User):
    saved = None
    factory = None
    if payload.conversation_id:
        try:
            saved = assistant_history.begin(db, user.customer_id, payload)
        except IntegrityError:
            db.rollback()
            saved = assistant_history.begin(db, user.customer_id, payload)
        payload = saved.payload
        factory = sessionmaker(bind=db.get_bind())
    record_answer = None
    if payload.mode == "records" and (saved is None or saved.cached_answer is None):
        record_answer = assistant_service.answer_question(db, user.customer_id, payload.question, payload.follow_up_topic)
    db.rollback()
    return StreamingResponse(
        _stream(payload, record_answer, saved, factory), media_type="text/event-stream",
        headers={"Cache-Control": "private, no-store", "X-Accel-Buffering": "no"},
    )
