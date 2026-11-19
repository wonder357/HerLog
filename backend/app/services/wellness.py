from __future__ import annotations

from datetime import date
from secrets import compare_digest
from uuid import uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import local_today, to_utc_naive, utc_now
from app.core.config import settings
from app.core.errors import conflict, invalid, not_found
from app.models.wellness import Checkin, GroupMembership, GroupReply, GroupShare, ShareReport, SkinJournal
from app.models.private_photo import CheckinPhoto
from app.schemas.wellness import CheckinIn, ShareIn, SkinJournalIn, SkinJournalOut
from app.services.cycle_context import current_phase
from app.services import private_photo

ACTIVITIES = {
    "walk": ("散步", "选择熟悉的路线，以自己舒服的节奏活动。"),
    "mobility": ("舒缓活动", "在舒服的范围内慢慢活动肩、背和髋部，随时可以停下。"),
    "strength": ("基础力量", "选一个已经熟悉的动作，按自己舒服的强度完成。"),
    "cycle": ("轻松骑行", "选熟悉的路线或在室内活动，时长由你决定。"),
    "rest": ("休息", "今天可以休息，也可以只记下当下的感受。"),
}
PHASE_ORDER = {
    "menstrual": ("mobility", "rest", "walk", "strength", "cycle"),
    "follicular": ("strength", "walk", "cycle", "mobility", "rest"),
    "ovulatory": ("cycle", "walk", "strength", "mobility", "rest"),
    "luteal": ("walk", "mobility", "rest", "cycle", "strength"),
    "unknown": ("walk", "mobility", "strength", "cycle", "rest"),
}
PHASE_NAMES = {
    "menstrual": "经期同行",
    "follicular": "卵泡期同行",
    "ovulatory": "排卵期同行",
    "luteal": "黄体期同行",
}
EXERCISE_CAPTIONS = {
    "checked_in": "记下了今天的活动。",
    "kept_it_light": "今天选了适合自己的节奏。",
    "made_time": "今天给自己留了一点时间。",
}
SKIN_CAPTIONS = {
    "care_routine": "今天记下了自己的护理步骤。",
    "sun_care": "今天记了一次日光防护。",
    "reflection": "今天给自己的皮肤感受留了个记录。",
}
SKIN_REPLIES = {
    "also_record": "我也在记护理日记。",
    "thanks": "谢谢分享。",
    "keep_observing": "可以留意自己接下来的感受。",
}


def checkin_out(row: Checkin, has_photo: bool = False) -> dict:
    return {
        "id": row.id, "activity_code": row.activity_code,
        "started_at": row.started_at.isoformat() + "Z",
        "duration_minutes": row.duration_minutes, "effort": row.effort,
        "feeling_code": row.feeling_code,
        "has_photo": has_photo,
    }


def create_checkin(session: Session, customer_id: str, payload: CheckinIn) -> dict:
    attributes = payload.model_dump(exclude={"client_key", "photo"})
    photo = private_photo.prepare(payload.photo)
    moment = to_utc_naive(payload.started_at)
    attributes["started_at"] = moment.replace(microsecond=moment.microsecond // 1000 * 1000)
    row = Checkin(customer_id=customer_id, client_key=payload.client_key, **attributes)
    session.add(row)
    try:
        if photo is not None:
            session.flush()
            private_photo.replace(session, CheckinPhoto, row.id, photo)
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(select(Checkin).where(
            Checkin.customer_id == customer_id, Checkin.client_key == payload.client_key
        ))
        if existing is None:
            raise
        digest = private_photo.digest_for(session, CheckinPhoto, existing.id)
        if any(getattr(existing, key) != value for key, value in attributes.items()) or digest != (photo.digest if photo else None):
            raise conflict("这次请求已用于另一条打卡")
        return checkin_out(existing, digest is not None)
    return checkin_out(row, photo is not None)


def member_checkin(session: Session, customer_id: str, checkin_id: int, *, lock: bool = False) -> Checkin:
    query = select(Checkin).where(Checkin.customer_id == customer_id, Checkin.id == checkin_id)
    row = session.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise not_found()
    return row


def withdraw_reference(session: Session, customer_id: str, topic: str, reference_key: str) -> None:
    session.execute(update(GroupShare).where(
        GroupShare.customer_id == customer_id, GroupShare.topic == topic,
        GroupShare.reference_key == reference_key,
    ).values(status="withdrawn"))


def save_journal(session: Session, customer_id: str, day: date, payload: SkinJournalIn) -> SkinJournalOut:
    if day > local_today():
        raise invalid("请选择今天或过去的日期")
    data = payload.model_dump()
    data["sensations"] = list(dict.fromkeys(payload.sensations))
    data["routine"] = list(dict.fromkeys(payload.routine))
    data["note"] = (payload.note or "").strip() or None
    if not any(data.values()):
        raise invalid("请至少记录一项感受或护理内容")
    row = session.get(SkinJournal, (customer_id, day))
    if row is None:
        row = SkinJournal(customer_id=customer_id, day=day, **data)
        session.add(row)
    else:
        for key, value in data.items():
            setattr(row, key, value)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.get(SkinJournal, (customer_id, day))
        if existing is None:
            raise
        for key, value in data.items():
            setattr(existing, key, value)
        session.commit()
    return SkinJournalOut(day=day, **data)


def group_options(session: Session, customer_id: str, topic: str) -> list[dict]:
    memberships = set(session.scalars(select(GroupMembership.group_key).where(
        GroupMembership.customer_id == customer_id, GroupMembership.topic == topic,
    )))
    allowed = {"general": "日常运动同行" if topic == "exercise" else "护理经验小组"}
    if topic == "exercise":
        phase = current_phase(session, customer_id, local_today()).phase
        if phase in PHASE_NAMES:
            allowed[phase] = PHASE_NAMES[phase]
        for key in sorted(memberships - {"general"}):
            allowed.setdefault(key, PHASE_NAMES[key])
    return [{"group_key": key, "title": title, "joined": key in memberships}
            for key, title in allowed.items()]


def join_group(session: Session, customer_id: str, topic: str, key: str, supplied_code: str) -> None:
    membership_key = (customer_id, topic, key)
    if session.get(GroupMembership, membership_key):
        return
    if key not in {group["group_key"] for group in group_options(session, customer_id, topic)}:
        raise not_found()
    expected = settings.HERLOG_GROUP_INVITE_CODE
    if not expected or not compare_digest(expected.encode(), supplied_code.strip().encode()):
        raise not_found("小组或邀请码不可用")
    session.add(GroupMembership(
        customer_id=customer_id, topic=topic, group_key=key, consented_at=utc_now()
    ))
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        if session.get(GroupMembership, membership_key) is None:
            raise


def require_group(session: Session, customer_id: str, topic: str, key: str) -> None:
    if session.get(GroupMembership, (customer_id, topic, key)) is None:
        raise not_found()


def leave_group(session: Session, customer_id: str, topic: str, key: str) -> None:
    require_group(session, customer_id, topic, key)
    session.execute(update(GroupShare).where(
        GroupShare.customer_id == customer_id, GroupShare.topic == topic, GroupShare.group_key == key,
    ).values(status="withdrawn"))
    session.execute(delete(GroupMembership).where(
        GroupMembership.customer_id == customer_id, GroupMembership.topic == topic,
        GroupMembership.group_key == key,
    ))
    session.commit()


def share_out(row: GroupShare, customer_id: str) -> dict:
    return {
        "public_id": row.public_id, "group_key": row.group_key, "status": row.status,
        "mine": row.customer_id == customer_id, "snapshot": row.snapshot,
        "display_name": "匿名成员",
    }


def publish(session: Session, customer_id: str, topic: str, payload: ShareIn) -> dict:
    require_group(session, customer_id, topic, payload.group_key)
    if topic == "exercise" and payload.checkin_id and payload.day is None:
        checkin = member_checkin(session, customer_id, payload.checkin_id)
        caption = EXERCISE_CAPTIONS.get(payload.caption_code)
        reference = str(checkin.id)
        snapshot = {"caption": caption, "activity": ACTIVITIES[checkin.activity_code][0]}
        if payload.include_duration_bucket and checkin.duration_minutes and checkin.activity_code != "rest":
            minutes = checkin.duration_minutes
            snapshot["duration_bucket"] = "十分钟以内" if minutes < 10 else "十至二十九分钟" if minutes < 30 else "三十分钟或以上"
    elif topic == "skin" and payload.day and payload.checkin_id is None and not payload.include_duration_bucket:
        if session.get(SkinJournal, (customer_id, payload.day)) is None:
            raise not_found()
        caption = SKIN_CAPTIONS.get(payload.caption_code)
        reference = payload.day.isoformat()
        snapshot = {"caption": caption}
    else:
        raise invalid("请选择一条自己的记录")
    if not caption:
        raise invalid("请选择适用于当前小组的分享内容")
    row = GroupShare(
        public_id=uuid4().hex, customer_id=customer_id, topic=topic, group_key=payload.group_key,
        reference_key=reference, client_key=payload.client_key, snapshot=snapshot,
        status="published", published_at=utc_now(),
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        previous = session.scalar(select(GroupShare).where(
            GroupShare.customer_id == customer_id, GroupShare.topic == topic,
            GroupShare.client_key == payload.client_key,
        ))
        if previous is None:
            raise conflict("这条记录在此小组已有分享")
        if previous.reference_key != reference or previous.group_key != payload.group_key or previous.snapshot != snapshot:
            raise conflict("这次请求已用于另一张分享卡")
        return share_out(previous, customer_id)
    return share_out(row, customer_id)


def feed(session: Session, customer_id: str, topic: str, key: str, cursor: int | None) -> dict:
    require_group(session, customer_id, topic, key)
    statement = select(GroupShare).where(
        GroupShare.topic == topic, GroupShare.group_key == key, GroupShare.status == "published",
        select(GroupMembership.customer_id).where(
            GroupMembership.customer_id == GroupShare.customer_id,
            GroupMembership.topic == GroupShare.topic,
            GroupMembership.group_key == GroupShare.group_key,
        ).exists(),
        ~select(ShareReport.share_id).where(
            ShareReport.share_id == GroupShare.id, ShareReport.customer_id == customer_id
        ).exists(),
    )
    if cursor is not None:
        statement = statement.where(GroupShare.id < cursor)
    rows = list(session.scalars(statement.order_by(GroupShare.id.desc()).limit(21)))
    items = [share_out(row, customer_id) for row in rows[:20]]
    if topic == "skin" and items:
        by_id = {row.id: item for row, item in zip(rows, items)}
        for item in items:
            item["replies"] = []
        replies = session.execute(
            select(GroupReply.share_id, GroupReply.reply_code, func.count())
            .where(GroupReply.share_id.in_(by_id))
            .group_by(GroupReply.share_id, GroupReply.reply_code)
        )
        for share_id, code, count in replies:
            by_id[share_id]["replies"].append({"text": SKIN_REPLIES[code], "count": count})
    return {
        "items": items,
        "next_cursor": rows[19].id if len(rows) == 21 else None,
    }


def group_share(session: Session, topic: str, public_id: str) -> GroupShare:
    row = session.scalar(select(GroupShare).where(GroupShare.topic == topic, GroupShare.public_id == public_id))
    if row is None:
        raise not_found()
    return row


def report_share(session: Session, customer_id: str, topic: str, public_id: str, reason: str) -> None:
    share = group_share(session, topic, public_id)
    require_group(session, customer_id, topic, share.group_key)
    if session.get(ShareReport, (share.id, customer_id)) is not None:
        return
    if share.status != "published" or share.customer_id == customer_id:
        raise not_found()
    report = ShareReport(share_id=share.id, customer_id=customer_id, reason_code=reason, created_at=utc_now())
    session.add(report)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        if session.get(ShareReport, (share.id, customer_id)) is None:
            raise


def reply_to_skin_share(session: Session, customer_id: str, public_id: str, code: str) -> None:
    share = group_share(session, "skin", public_id)
    require_group(session, customer_id, "skin", share.group_key)
    if share.status != "published" or session.get(ShareReport, (share.id, customer_id)) is not None:
        raise not_found()
    key = (share.id, customer_id)
    reply = session.get(GroupReply, key)
    if reply is None:
        session.add(GroupReply(share_id=share.id, customer_id=customer_id, reply_code=code))
    else:
        reply.reply_code = code
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        previous = session.get(GroupReply, key)
        if previous is None:
            raise
        previous.reply_code = code
        session.commit()


def recommendations(session: Session, customer_id: str, day: date, include_cycle: bool) -> dict:
    phase = current_phase(session, customer_id, day) if include_cycle else None
    order = PHASE_ORDER[phase.phase if phase else "unknown"]
    return {
        "phase": phase,
        "cards": [{"activity_code": key, "title": ACTIVITIES[key][0], "instructions": ACTIVITIES[key][1]}
                  for key in order],
    }
