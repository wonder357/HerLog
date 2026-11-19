from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, own_account
from app.db.session import get_session
from app.models.home import HomePreference
from app.schemas.common import ApiResponse
from app.schemas.home import PasswordChange, RecordingChanges, ReminderChanges
from app.services import home_service
from app.services.auth_service import CurrentUser
from app.services.cycle_context import current_phase


router = APIRouter(prefix="/herlog", tags=["home"], dependencies=[Depends(own_account)])
SessionDep = Annotated[Session, Depends(get_session)]
UserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.get("/overview")
def overview(month: Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")], session: SessionDep, user: UserDep):
    return ApiResponse(data=home_service.overview(session, user.customer_id, month))


@router.get("/cycle-context")
def cycle_context(day: date, session: SessionDep, user: UserDep):
    return ApiResponse(data=current_phase(session, user.customer_id, day))


@router.get("/health-summary")
def health_summary(session: SessionDep, user: UserDep):
    return ApiResponse(data=home_service.health_summary(session, user.customer_id))


def reminders(row: HomePreference | None) -> ApiResponse:
    values = home_service.preference_view(row, ReminderChanges().model_dump())
    return ApiResponse(data={**values, "delivery_status": "preference_only"})


@router.get("/reminder-settings")
def read_reminders(session: SessionDep, user: UserDep):
    return reminders(session.get(HomePreference, user.customer_id))


@router.put("/reminder-settings")
def write_reminders(payload: ReminderChanges, session: SessionDep, user: UserDep):
    return reminders(home_service.update_preferences(session, user.customer_id, payload.model_dump(exclude_unset=True)))


@router.get("/recording-preferences")
def read_recording(session: SessionDep, user: UserDep):
    row = session.get(HomePreference, user.customer_id)
    return ApiResponse(data=home_service.preference_view(row, RecordingChanges().model_dump()))


@router.put("/recording-preferences")
def write_recording(payload: RecordingChanges, session: SessionDep, user: UserDep):
    row = home_service.update_preferences(session, user.customer_id, payload.model_dump(exclude_unset=True))
    return ApiResponse(data=home_service.preference_view(row, RecordingChanges().model_dump()))


@router.put("/account/password")
def change_password(payload: PasswordChange, session: SessionDep, user: UserDep):
    home_service.change_password(session, user.customer_id, payload.current_password.get_secret_value(), payload.new_password.get_secret_value())
    return ApiResponse(data={"reauth_required": True})
