from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.schemas.common import ApiResponse
from app.schemas.fertility import DailyIn, DailyOut, ModeIn, PreferenceOut, StartDateIn
from app.services import fertility_service as service
from app.services.auth_service import CurrentUser

router = APIRouter(prefix="/herlog", tags=["cycle preference and fertility journal"])


@router.get("/cycle-preference", response_model=ApiResponse[PreferenceOut])
def read_preference(session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user)):
    return ApiResponse(data=service.get_preference(session, user.customer_id))


@router.put("/cycle-preference", response_model=ApiResponse[PreferenceOut])
def update_mode(payload: ModeIn, session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user)):
    return ApiResponse(data=service.set_mode(session, user.customer_id, payload.active_mode))


@router.put("/cycle-preference/start-date", response_model=ApiResponse[PreferenceOut])
def update_start_date(payload: StartDateIn, session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user)):
    return ApiResponse(data=service.set_start_date(session, user.customer_id, payload.trying_started_on))


@router.get("/fertility-daily", response_model=ApiResponse[list[DailyOut]])
def list_days(
    day_from: date = Query(alias="from"),
    day_to: date = Query(alias="to"),
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
):
    return ApiResponse(data=service.list_daily(session, user.customer_id, day_from, day_to))


@router.get("/fertility-daily/{day}", response_model=ApiResponse[DailyOut])
def read_day(day: date, session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user)):
    return ApiResponse(data=service.get_daily(session, user.customer_id, day))


@router.put("/fertility-daily/{day}", response_model=ApiResponse[DailyOut])
def save_day(
    day: date, payload: DailyIn, session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user),
):
    return ApiResponse(data=service.save_daily(session, user.customer_id, day, payload))


@router.delete("/fertility-daily/{day}", response_model=ApiResponse[None])
def delete_day(
    day: date, expected_revision: UUID, session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user),
):
    service.delete_daily(session, user.customer_id, day, expected_revision)
    return ApiResponse(data=None)
