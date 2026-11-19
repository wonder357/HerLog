from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, own_account
from app.core.clock import local_today
from app.db.session import get_session
from app.models.private_photo import ProfilePhoto
from app.schemas.common import ApiResponse
from app.schemas.herlog import (
    FeelingIn,
    FeelingOut,
    PeriodIn,
    PeriodOut,
    ProfileOut,
    ProfileUpdate,
)
from app.services import feeling_service, period_service, private_photo, profile_service
from app.services.auth_service import CurrentUser

router = APIRouter(prefix="/herlog", tags=["herlog"])


@router.get("/profile", response_model=ApiResponse[ProfileOut], dependencies=[Depends(own_account)])
def read_profile(
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user)
) -> ApiResponse[ProfileOut]:
    return ApiResponse(data=profile_service.get_profile(session, user.customer_id))


@router.put("/profile", response_model=ApiResponse[ProfileOut], dependencies=[Depends(own_account)])
def write_profile(
    payload: ProfileUpdate,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[ProfileOut]:
    return ApiResponse(data=profile_service.update_profile(session, user.customer_id, payload))


@router.get("/profile/avatar", response_class=Response, dependencies=[Depends(own_account)])
def read_avatar(session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user)) -> Response:
    return private_photo.image_response(session, ProfilePhoto, user.customer_id)


@router.get("/periods", response_model=ApiResponse[dict])
def list_periods(
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user)
) -> ApiResponse[dict]:
    return ApiResponse(data=period_service.list_periods(session, user.customer_id))


@router.post("/periods", response_model=ApiResponse[PeriodOut])
def create_period(
    payload: PeriodIn,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[PeriodOut]:
    return ApiResponse(data=period_service.create_period(session, user.customer_id, payload))


@router.put("/periods/{period_id}", response_model=ApiResponse[PeriodOut])
def update_period(
    period_id: int,
    payload: PeriodIn,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[PeriodOut]:
    return ApiResponse(
        data=period_service.update_period(session, user.customer_id, period_id, payload)
    )


@router.delete("/periods/{period_id}", response_model=ApiResponse[None])
def delete_period(
    period_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[None]:
    period_service.delete_period(session, user.customer_id, period_id)
    return ApiResponse(data=None)


@router.get("/feelings", response_model=ApiResponse[list[FeelingOut]])
def list_feelings(
    day_from: date = Query(default_factory=local_today, alias="from"),
    day_to: date = Query(default_factory=local_today, alias="to"),
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[list[FeelingOut]]:
    return ApiResponse(data=feeling_service.list_feelings(session, user.customer_id, day_from, day_to))


@router.put("/feelings/{day}", response_model=ApiResponse[FeelingOut | None])
def upsert_feeling(
    day: date,
    payload: FeelingIn,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[FeelingOut | None]:
    return ApiResponse(data=feeling_service.upsert_feeling(session, user.customer_id, day, payload))


@router.delete("/feelings/{day}", response_model=ApiResponse[None])
def delete_feeling(
    day: date,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[None]:
    feeling_service.delete_feeling(session, user.customer_id, day)
    return ApiResponse(data=None)
