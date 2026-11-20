from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, pending_store
from app.db.session import get_session
from app.schemas.assistant_chat import ChatDetailOut, ChatRenameIn, ChatSummaryOut, summary_out
from app.schemas.common import ApiResponse
from app.schemas.herlog import (
    AssistantAnswerOut,
    AssistantQueryIn,
    AssistantStreamIn,
    SkinAnalysisOut,
    SkinAnalyzeIn,
    SkinObservationOut,
    SkinSaveIn,
    SkinSummaryOut,
)
from app.services import assistant_chat, assistant_service, assistant_stream, skin_service
from app.services.auth_service import CurrentUser
from app.services.pending_store import PendingStore

router = APIRouter(prefix="/herlog", tags=["herlog"])


@router.post("/skin/analyze", response_model=ApiResponse[SkinAnalysisOut])
def analyze_skin(
    payload: SkinAnalyzeIn,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
    store: PendingStore = Depends(pending_store),
) -> ApiResponse[SkinAnalysisOut]:
    return ApiResponse(data=skin_service.analyze(session, user.customer_id, payload, store))


@router.delete("/skin/pending/{analysis_id}", response_model=ApiResponse[None])
def discard_pending(
    analysis_id: str,
    user: CurrentUser = Depends(get_current_user),
    store: PendingStore = Depends(pending_store),
) -> ApiResponse[None]:
    skin_service.discard_pending(user.customer_id, analysis_id, store)
    return ApiResponse(data=None)


@router.post("/skin/observations", response_model=ApiResponse[SkinObservationOut])
def save_observation(
    payload: SkinSaveIn,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
    store: PendingStore = Depends(pending_store),
) -> ApiResponse[SkinObservationOut]:
    record, _created = skin_service.save_observation(
        session, user.customer_id, payload.analysis_id, store
    )
    return ApiResponse(data=record)


@router.get("/skin/observations", response_model=ApiResponse[list[SkinSummaryOut]])
def list_observations(
    site: str | None = None,
    day_from: date | None = Query(default=None, alias="from"),
    day_to: date | None = Query(default=None, alias="to"),
    limit: int | None = Query(default=None, ge=1, le=100),
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[list[SkinSummaryOut]]:
    return ApiResponse(
        data=skin_service.list_observations(session, user.customer_id, site, day_from, day_to, limit)
    )


@router.get("/skin/observations/{observation_id}", response_model=ApiResponse[SkinObservationOut])
def get_observation(
    observation_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[SkinObservationOut]:
    return ApiResponse(data=skin_service.get_observation(session, user.customer_id, observation_id))


@router.get("/skin/observations/{observation_id}/image")
def get_observation_image(
    observation_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    data, mime = skin_service.load_image(session, user.customer_id, observation_id)
    return Response(
        content=data,
        media_type=mime,
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/assistant/query", response_model=ApiResponse[AssistantAnswerOut])
def assistant_query(
    payload: AssistantQueryIn,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[AssistantAnswerOut]:
    return ApiResponse(
        data=assistant_service.answer_question(session, user.customer_id, payload.question, payload.follow_up_topic)
    )


@router.post("/assistant/stream", response_class=StreamingResponse)
def assistant_conversation(
    payload: AssistantStreamIn,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    record_answer = None
    if payload.mode == "records":
        record_answer = assistant_service.answer_question(
            session, user.customer_id, payload.question, payload.follow_up_topic
        )
    session.rollback()

    def save(answer: str, source: str) -> int:
        chat = assistant_chat.append_exchange(
            session,
            user.customer_id,
            payload.question,
            answer,
            source,
            chat_id=payload.chat_id,
        )
        session.commit()
        return chat.id

    return StreamingResponse(
        assistant_stream.stream_assistant(payload, record_answer, save),
        media_type="text/event-stream",
        headers={"Cache-Control": "private, no-store", "X-Accel-Buffering": "no"},
    )


@router.get("/assistant/chats", response_model=ApiResponse[list[ChatSummaryOut]])
def assistant_chat_list(
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[list[ChatSummaryOut]]:
    return ApiResponse(data=assistant_chat.list_chats(session, user.customer_id))


@router.get("/assistant/chats/{chat_id}", response_model=ApiResponse[ChatDetailOut])
def assistant_chat_detail(
    chat_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[ChatDetailOut]:
    return ApiResponse(data=assistant_chat.chat_detail(session, user.customer_id, chat_id))


@router.patch("/assistant/chats/{chat_id}", response_model=ApiResponse[ChatSummaryOut])
def assistant_chat_rename(
    chat_id: int,
    payload: ChatRenameIn,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[ChatSummaryOut]:
    chat = assistant_chat.rename_chat(session, user.customer_id, chat_id, payload.title)
    total = assistant_chat.message_count(session, user.customer_id, chat.id)
    session.commit()
    return ApiResponse(data=summary_out(chat.id, chat.title, total, chat.updated_at))


@router.delete("/assistant/chats/{chat_id}", response_model=ApiResponse[None])
def assistant_chat_delete(
    chat_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[None]:
    assistant_chat.delete_chat(session, user.customer_id, chat_id)
    session.commit()
    return ApiResponse(data=None)
