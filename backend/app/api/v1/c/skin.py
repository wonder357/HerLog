from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, pending_store
from app.db.session import get_session
from app.schemas.common import ApiResponse
from app.schemas.herlog import (
    AssistantAnswerOut,
    AssistantQueryIn,
    SkinAnalysisOut,
    SkinAnalyzeIn,
    SkinObservationOut,
    SkinSaveIn,
    SkinSummaryOut,
)
from app.services import assistant_service, skin_service
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
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[list[SkinSummaryOut]]:
    return ApiResponse(
        data=skin_service.list_observations(session, user.customer_id, site, day_from, day_to)
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
        data=assistant_service.answer_question(session, user.customer_id, payload.question)
    )
