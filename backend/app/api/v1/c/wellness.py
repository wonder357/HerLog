from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.clock import local_today
from app.core.config import settings
from app.core.errors import invalid, not_found
from app.db.session import get_session
from app.models.wellness import Checkin, GroupShare, ShareReport, SkinJournal
from app.schemas.common import ApiResponse
from app.schemas.wellness import (
    CheckinIn, GroupKey, JoinGroupIn, ModerationIn, ReplyIn, ReportIn, ShareIn,
    SkinJournalIn, SkinJournalOut, Topic,
)
from app.services import wellness
from app.services.auth_service import CurrentUser
from app.services.exercise_discussion import DISCUSSION_KEY
from app.services.period_service import lock_member

router = APIRouter(prefix="/herlog", tags=["wellness"])
Db = Annotated[Session, Depends(get_session)]
User = Annotated[CurrentUser, Depends(get_current_user)]


@router.get("/exercise/recommendations", response_model=ApiResponse[dict])
def exercise_recommendations(db: Db, user: User, day: date | None = None, include_cycle: bool = True):
    return ApiResponse(data=wellness.recommendations(db, user.customer_id, day or local_today(), include_cycle))


@router.get("/exercise/checkins", response_model=ApiResponse[list[dict]])
def exercise_list(db: Db, user: User, before_id: int | None = Query(default=None, ge=1)):
    statement = select(Checkin).where(Checkin.customer_id == user.customer_id)
    if before_id is not None:
        statement = statement.where(Checkin.id < before_id)
    rows = db.scalars(statement.order_by(Checkin.id.desc()).limit(40))
    return ApiResponse(data=[wellness.checkin_out(row) for row in rows])


@router.post("/exercise/checkins", response_model=ApiResponse[dict])
def exercise_create(payload: CheckinIn, db: Db, user: User):
    return ApiResponse(data=wellness.create_checkin(db, user.customer_id, payload))


@router.delete("/exercise/checkins/{checkin_id}", response_model=ApiResponse[None])
def exercise_delete(checkin_id: int, db: Db, user: User):
    lock_member(db, user.customer_id)
    row = wellness.member_checkin(db, user.customer_id, checkin_id, lock=True)
    wellness.withdraw_reference(db, user.customer_id, "exercise", str(row.id))
    db.delete(row)
    db.commit()
    return ApiResponse(data=None)


@router.get("/exercise/checkins/{checkin_id}", response_model=ApiResponse[dict])
def exercise_get(checkin_id: int, db: Db, user: User):
    return ApiResponse(data=wellness.checkin_out(wellness.member_checkin(db, user.customer_id, checkin_id)))


@router.get("/skin/journal", response_model=ApiResponse[list[SkinJournalOut]])
def skin_journal_range(
    db: Db, user: User, response: Response,
    day_from: date | None = Query(default=None, alias="from"),
    day_to: date | None = Query(default=None, alias="to"),
):
    response.headers["Cache-Control"] = "private, no-store"
    end = day_to or local_today()
    start = day_from or max(date.min, end - timedelta(days=min(30, (end - date.min).days)))
    if start > end or (end - start).days > 61:
        raise invalid("请选择连续两个月内的日期范围")
    rows = db.scalars(select(SkinJournal).where(
        SkinJournal.customer_id == user.customer_id, SkinJournal.day.between(start, end),
    ).order_by(SkinJournal.day.desc()))
    return ApiResponse(data=[SkinJournalOut.model_validate(row, from_attributes=True) for row in rows])


@router.get("/skin/journal/latest", response_model=ApiResponse[SkinJournalOut | None])
def skin_journal_latest(db: Db, user: User, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    row = db.scalar(select(SkinJournal).where(SkinJournal.customer_id == user.customer_id)
                    .order_by(SkinJournal.day.desc()).limit(1))
    return ApiResponse(data=SkinJournalOut.model_validate(row, from_attributes=True) if row else None)


@router.put("/skin/journal/{day}", response_model=ApiResponse[SkinJournalOut])
def skin_journal_save(day: date, payload: SkinJournalIn, db: Db, user: User):
    return ApiResponse(data=wellness.save_journal(db, user.customer_id, day, payload))


@router.delete("/skin/journal/{day}", response_model=ApiResponse[None])
def skin_journal_delete(day: date, db: Db, user: User):
    row = db.get(SkinJournal, (user.customer_id, day))
    if row is None:
        raise not_found()
    wellness.withdraw_reference(db, user.customer_id, "skin", day.isoformat())
    db.delete(row)
    db.commit()
    return ApiResponse(data=None)


@router.get("/{topic}/groups", response_model=ApiResponse[list[dict]])
def groups(topic: Topic, db: Db, user: User, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    return ApiResponse(data=wellness.group_options(db, user.customer_id, topic))


@router.post("/{topic}/groups/{group_key}/membership", response_model=ApiResponse[None])
def join(topic: Topic, group_key: GroupKey, payload: JoinGroupIn, db: Db, user: User):
    wellness.join_group(db, user.customer_id, topic, group_key, payload.invite_code)
    return ApiResponse(data=None)


@router.delete("/{topic}/groups/{group_key}/membership", response_model=ApiResponse[None])
def leave(topic: Topic, group_key: GroupKey, db: Db, user: User):
    wellness.leave_group(db, user.customer_id, topic, group_key)
    return ApiResponse(data=None)


@router.get("/{topic}/groups/{group_key}/shares", response_model=ApiResponse[dict])
def group_feed(
    topic: Topic, group_key: GroupKey, db: Db, user: User, response: Response,
    cursor: int | None = Query(default=None, ge=1),
):
    response.headers["Cache-Control"] = "private, no-store"
    return ApiResponse(data=wellness.feed(db, user.customer_id, topic, group_key, cursor))


@router.get("/{topic}/shares/mine", response_model=ApiResponse[list[dict]])
def my_shares(topic: Topic, db: Db, user: User, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    rows = db.scalars(select(GroupShare).where(
        GroupShare.customer_id == user.customer_id, GroupShare.topic == topic, GroupShare.group_key != DISCUSSION_KEY,
    ).order_by(GroupShare.id.desc()).limit(40))
    return ApiResponse(data=[wellness.share_out(row, user.customer_id) for row in rows])


@router.post("/{topic}/shares", response_model=ApiResponse[dict])
def publish(topic: Topic, payload: ShareIn, db: Db, user: User):
    return ApiResponse(data=wellness.publish(db, user.customer_id, topic, payload))


@router.delete("/{topic}/shares/{public_id}", response_model=ApiResponse[None])
def revoke(topic: Topic, public_id: str, db: Db, user: User):
    row = wellness.group_share(db, topic, public_id)
    if row.customer_id != user.customer_id:
        raise not_found()
    row.status = "withdrawn"
    db.commit()
    return ApiResponse(data=None)


@router.post("/{topic}/shares/{public_id}/reports", response_model=ApiResponse[None])
def report(topic: Topic, public_id: str, payload: ReportIn, db: Db, user: User):
    wellness.report_share(db, user.customer_id, topic, public_id, payload.reason_code)
    return ApiResponse(data=None)


@router.post("/skin/shares/{public_id}/replies", response_model=ApiResponse[None])
def skin_reply(public_id: str, payload: ReplyIn, db: Db, user: User):
    wellness.reply_to_skin_share(db, user.customer_id, public_id, payload.reply_code)
    return ApiResponse(data=None)


@router.put("/{topic}/shares/{public_id}/moderation", response_model=ApiResponse[None])
def moderate(topic: Topic, public_id: str, payload: ModerationIn, db: Db, user: User):
    if user.customer_id != settings.HERLOG_GROUP_MODERATOR_ID:
        raise not_found()
    row = wellness.group_share(db, topic, public_id)
    if row.status == "published" and payload.action == "hide":
        row.status = "hidden"
        db.commit()
    return ApiResponse(data=None)


@router.get("/{topic}/moderation/reports", response_model=ApiResponse[list[dict]])
def moderation_reports(topic: Topic, db: Db, user: User, response: Response):
    if user.customer_id != settings.HERLOG_GROUP_MODERATOR_ID:
        raise not_found()
    response.headers["Cache-Control"] = "private, no-store"
    rows = db.execute(
        select(GroupShare.public_id, GroupShare.snapshot, ShareReport.reason_code, ShareReport.created_at)
        .join(ShareReport, ShareReport.share_id == GroupShare.id)
        .where(GroupShare.topic == topic, GroupShare.status == "published")
        .order_by(ShareReport.created_at.desc()).limit(50)
    )
    return ApiResponse(data=[
        {"public_id": row.public_id, "snapshot": row.snapshot, "reason_code": row.reason_code,
         "reported_at": row.created_at.isoformat() + "Z"}
        for row in rows
    ])
