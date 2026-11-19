from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.schemas.common import ApiResponse
from app.schemas.herlog import WeightIn, WeightListOut, WeightOut, WeightSummaryOut, weight_out
from app.services import weight_service
from app.services.auth_service import CurrentUser

router = APIRouter(prefix="/herlog/weights", tags=["herlog"])


@router.get("", response_model=ApiResponse[WeightListOut])
def list_weights(
    day_from: date | None = Query(default=None, alias="from"),
    day_to: date | None = Query(default=None, alias="to"),
    tag: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[WeightListOut]:
    return ApiResponse(
        data=weight_service.list_weights(
            session, user.customer_id, day_from, day_to, tag, page, page_size
        )
    )


@router.get("/summary", response_model=ApiResponse[WeightSummaryOut])
def weight_summary(
    days: int = Query(default=30, description="只支持 7 或 30"),
    include_cycle: bool = False,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[WeightSummaryOut]:
    return ApiResponse(data=weight_service.summary(session, user.customer_id, days, include_cycle))


@router.post("", response_model=ApiResponse[WeightOut])
def create_weight(
    payload: WeightIn,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[WeightOut]:
    record, _created = weight_service.create_weight(session, user.customer_id, payload)
    return ApiResponse(data=record)


@router.put("/{weight_id}", response_model=ApiResponse[WeightOut])
def update_weight(
    weight_id: int,
    payload: WeightIn,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[WeightOut]:
    return ApiResponse(data=weight_service.update_weight(session, user.customer_id, weight_id, payload))


@router.get("/{weight_id}", response_model=ApiResponse[WeightOut])
def get_weight(
    weight_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[WeightOut]:
    return ApiResponse(data=weight_out(weight_service.owned_weight(session, user.customer_id, weight_id)))


@router.delete("/{weight_id}", response_model=ApiResponse[None])
def delete_weight(
    weight_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[None]:
    weight_service.delete_weight(session, user.customer_id, weight_id)
    return ApiResponse(data=None)
