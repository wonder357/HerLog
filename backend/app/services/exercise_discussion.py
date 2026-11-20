from __future__ import annotations

import re
import unicodedata
from datetime import timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.errors import ApiError, conflict, invalid, not_found
from app.models.wellness import DiscussionReaction, DiscussionReply, DiscussionReplyReport, GroupShare, ShareReport
from app.schemas.discussion import DiscussionEditIn, DiscussionPostIn, DiscussionReplyIn
from app.services.period_service import lock_member
from app.services.wellness import ACTIVITIES, member_checkin

DISCUSSION_KEY = "discussion"
PAGE_SIZE = 20
# 这里只拦截常见的直接披露和违规用语，语境问题可由用户举报。
PRIVATE_TEXT = re.compile(
    r"https?://|www\.|[\w.+-]+@[\w.-]+\.[a-z]{2,}|(?<!\d)(?:\d[ -]?){10,}\d(?!\d)"
    r"|(?:微信号|手机号|联系电话|身份证号)|(?:\d+(?:\.\d+)?\s*(?:kg(?![a-z])|公斤|千克|斤|lbs?(?![a-z])))"
    r"|(?:体重|体脂(?:率)?)\s*[:=：为是约]?\s*\d"
)
HARMFUL_TEXT = re.compile(
    r"催吐|泻药减肥|绝食|极端节食|三天不吃|七天不吃|饿瘦|减肥药|代餐减肥|断水减重|肥猪|死胖子|胖成猪|身材羞辱"
    r"|(?:每天|每日|一天)\s*(?:只|仅)?\s*(?:吃|摄入)\s*\d{1,3}\s*(?:卡|大卡|千卡|kcal)"
)


def _check_text(*values: str) -> None:
    for value in values:
        text = "".join(char for char in unicodedata.normalize("NFKC", value).lower()
                       if unicodedata.category(char) != "Cf")
        if not any(char.isalnum() for char in text):
            raise invalid("请填写可阅读的讨论内容")
        if PRIVATE_TEXT.search(text):
            raise invalid("请移除体重或体脂数字、联系方式和外链后再发布")
        if HARMFUL_TEXT.search(re.sub(r"\s+", "", text)):
            raise invalid("请围绕运动体验讨论，移除节食方法或身材评价")


def _public_posts():
    return select(GroupShare).where(GroupShare.topic == "exercise", GroupShare.group_key == DISCUSSION_KEY)


def _public_post(session: Session, post_id: str, *, lock: bool = False) -> GroupShare:
    query = _public_posts().where(GroupShare.public_id == post_id)
    row = session.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise not_found()
    return row


def _visible_post(session: Session, customer_id: str, post_id: str, *, lock: bool = False) -> GroupShare:
    row = _public_post(session, post_id, lock=lock)
    if row.status != "published" or session.get(ShareReport, (row.id, customer_id)):
        raise not_found()
    return row


def _iso(moment):
    return moment.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _post_out(post: GroupShare, customer_id: str, reply_count: int = 0, **reactions) -> dict:
    return {
        "public_id": post.public_id, "category": post.snapshot["category"], "title": post.snapshot["title"],
        "body": post.snapshot["body"], "activity": post.snapshot.get("activity"),
        "published_at": _iso(post.published_at), "mine": post.customer_id == customer_id, "reply_count": reply_count,
        "like_count": 0, "liked": False, "saved": False, **reactions,
    }


def _reply_out(row: DiscussionReply, customer_id: str) -> dict:
    return {
        "public_id": row.public_id, "body": row.body, "published_at": _iso(row.published_at),
        "mine": row.customer_id == customer_id,
    }


def _visible_replies(customer_id: str):
    return (
        DiscussionReply.status == "published",
        ~select(DiscussionReplyReport.reply_id).where(
            DiscussionReplyReport.reply_id == DiscussionReply.id,
            DiscussionReplyReport.customer_id == customer_id,
        ).exists(),
    )


def _like_count():
    return select(func.count()).select_from(DiscussionReaction).where(
        DiscussionReaction.share_id == GroupShare.id, DiscussionReaction.kind == "like",
    ).correlate(GroupShare).scalar_subquery()


def _reaction_states(session: Session, customer_id: str, ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    likes = dict(session.execute(
        select(DiscussionReaction.share_id, func.count()).where(
            DiscussionReaction.share_id.in_(ids), DiscussionReaction.kind == "like",
        ).group_by(DiscussionReaction.share_id)
    ).all())
    own = set(session.execute(select(DiscussionReaction.share_id, DiscussionReaction.kind).where(
        DiscussionReaction.share_id.in_(ids), DiscussionReaction.customer_id == customer_id,
    )))
    return {
        post_id: {"like_count": likes.get(post_id, 0), "liked": (post_id, "like") in own,
                  "saved": (post_id, "save") in own}
        for post_id in ids
    }


def list_posts(session: Session, customer_id: str, category: str | None, cursor: int | None, *,
               q: str | None = None, view: str = "all", sort: str = "latest", cursor_likes: int | None = None) -> dict:
    query = _public_posts().where(
        GroupShare.status == "published",
        ~select(ShareReport.share_id).where(
            ShareReport.share_id == GroupShare.id, ShareReport.customer_id == customer_id,
        ).exists(),
    )
    if category:
        query = query.where(GroupShare.snapshot["category"].as_string() == category)
    if keyword := (q or "").strip():
        query = query.where(or_(
            GroupShare.snapshot["title"].as_string().icontains(keyword, autoescape=True),
            GroupShare.snapshot["body"].as_string().icontains(keyword, autoescape=True),
        ))
    if view == "mine":
        query = query.where(GroupShare.customer_id == customer_id)
    elif view == "saved":
        query = query.where(select(DiscussionReaction.share_id).where(
            DiscussionReaction.share_id == GroupShare.id, DiscussionReaction.kind == "save",
            DiscussionReaction.customer_id == customer_id,
        ).exists())
    if sort == "popular":
        likes = _like_count()
        if cursor is not None:
            if cursor_likes is None:
                raise invalid("热门分页缺少点赞游标")
            query = query.where(or_(likes < cursor_likes, (likes == cursor_likes) & (GroupShare.id < cursor)))
        query = query.add_columns(likes.label("rank_likes")).order_by(likes.desc())
    elif cursor is not None:
        query = query.where(GroupShare.id < cursor)
    rows = session.execute(query.order_by(GroupShare.id.desc()).limit(PAGE_SIZE + 1)).all()
    page = [result[0] for result in rows[:PAGE_SIZE]]
    ids = [row.id for row in page]
    states = _reaction_states(session, customer_id, ids)
    counts = dict(session.execute(
        select(DiscussionReply.share_id, func.count()).where(
            DiscussionReply.share_id.in_(ids), *_visible_replies(customer_id),
        ).group_by(DiscussionReply.share_id),
    ).all()) if page else {}
    result = {
        "items": [_post_out(row, customer_id, counts.get(row.id, 0), **states[row.id]) for row in page],
        "next_cursor": page[-1].id if len(rows) > PAGE_SIZE else None,
    }
    if sort == "popular":
        result["next_cursor_likes"] = rows[PAGE_SIZE - 1].rank_likes if len(rows) > PAGE_SIZE else None
    return result


def edit_post(session: Session, customer_id: str, post_id: str, payload: DiscussionEditIn) -> None:
    row = _visible_post(session, customer_id, post_id, lock=True)
    if row.customer_id != customer_id:
        raise not_found()
    _check_text(payload.title, payload.body)
    row.snapshot = {**row.snapshot, **payload.model_dump()}
    session.commit()


def set_reaction(session: Session, customer_id: str, post_id: str, kind: str, enabled: bool) -> dict:
    post = _visible_post(session, customer_id, post_id, lock=True)
    current = session.get(DiscussionReaction, (post.id, kind, customer_id))
    if enabled and current is None:
        session.add(DiscussionReaction(share_id=post.id, kind=kind, customer_id=customer_id))
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            post = _visible_post(session, customer_id, post_id, lock=True)
            if session.get(DiscussionReaction, (post.id, kind, customer_id)) is None:
                raise
    elif not enabled and current is not None:
        session.delete(current)
        session.flush()
    state = _reaction_states(session, customer_id, [post.id])[post.id]
    session.commit()
    return state


def publish(session: Session, customer_id: str, payload: DiscussionPostIn) -> dict:
    _check_text(payload.title, payload.body)
    lock_member(session, customer_id)
    post_id = uuid4().hex
    snapshot = {"category": payload.category, "title": payload.title, "body": payload.body}
    if payload.checkin_id is not None:
        entry = member_checkin(session, customer_id, payload.checkin_id, lock=True)
        snapshot["activity"] = ACTIVITIES[entry.activity_code][0]
    reference = str(payload.checkin_id) if payload.checkin_id is not None else post_id
    original = session.scalar(_public_posts().where(
        GroupShare.customer_id == customer_id, GroupShare.client_key == payload.client_key,
    ).with_for_update())
    if original is not None:
        if original.status != "published" or original.snapshot != snapshot or (
            payload.checkin_id is not None and original.reference_key != reference
        ):
            raise conflict("这次请求已用于另一条讨论，请重新发布")
        return _post_out(original, customer_id)

    now = utc_now()
    recent = session.scalar(select(func.count()).select_from(GroupShare).where(
        GroupShare.customer_id == customer_id, GroupShare.topic == "exercise", GroupShare.group_key == DISCUSSION_KEY,
        GroupShare.published_at >= now - timedelta(minutes=10),
    ))
    if recent >= 5:
        raise ApiError(429, "发帖较频繁，请稍后再试")
    row = GroupShare(
        public_id=post_id, customer_id=customer_id, topic="exercise", group_key=DISCUSSION_KEY,
        reference_key=reference, client_key=payload.client_key, snapshot=snapshot, status="published",
        published_at=now,
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        original = session.scalar(_public_posts().where(
            GroupShare.customer_id == customer_id, GroupShare.client_key == payload.client_key,
        ))
        if original is not None and original.status == "published" and original.snapshot == snapshot and (
            payload.checkin_id is None or original.reference_key == reference
        ):
            return _post_out(original, customer_id)
        raise conflict("该打卡已有公开讨论，或发布请求已使用")
    return _post_out(row, customer_id)


def remove_post(session: Session, customer_id: str, post_id: str) -> None:
    row = _public_post(session, post_id, lock=True)
    if row.customer_id != customer_id:
        raise not_found()
    row.status = "withdrawn"
    session.commit()


def list_replies(session: Session, customer_id: str, post_id: str, cursor: int | None) -> dict:
    post = _visible_post(session, customer_id, post_id)
    query = select(DiscussionReply).where(DiscussionReply.share_id == post.id, *_visible_replies(customer_id))
    if cursor is not None:
        query = query.where(DiscussionReply.id < cursor)
    rows = list(session.scalars(query.order_by(DiscussionReply.id.desc()).limit(PAGE_SIZE + 1)))
    return {
        "items": [_reply_out(row, customer_id) for row in rows[:PAGE_SIZE]],
        "next_cursor": rows[PAGE_SIZE - 1].id if len(rows) > PAGE_SIZE else None,
    }


def reply(session: Session, customer_id: str, post_id: str, payload: DiscussionReplyIn) -> dict:
    _check_text(payload.body)
    post = _visible_post(session, customer_id, post_id, lock=True)
    row = DiscussionReply(
        public_id=uuid4().hex, share_id=post.id, customer_id=customer_id,
        body=payload.body, client_key=payload.client_key, published_at=utc_now(), status="published",
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        original = session.scalar(select(DiscussionReply).where(
            DiscussionReply.share_id == post.id, DiscussionReply.customer_id == customer_id,
            DiscussionReply.client_key == payload.client_key,
        ))
        if original is None or original.body != payload.body or original.status != "published":
            raise conflict("这次请求已用于另一条回复")
        return _reply_out(original, customer_id)
    return _reply_out(row, customer_id)


def _reply_row(session: Session, post: GroupShare, reply_id: str) -> DiscussionReply:
    row = session.scalar(select(DiscussionReply).where(
        DiscussionReply.share_id == post.id, DiscussionReply.public_id == reply_id,
    ).with_for_update())
    if row is None:
        raise not_found()
    return row


def remove_reply(session: Session, customer_id: str, post_id: str, reply_id: str) -> None:
    post = _visible_post(session, customer_id, post_id, lock=True)
    row = _reply_row(session, post, reply_id)
    if row.customer_id != customer_id:
        raise not_found()
    row.status = "withdrawn"
    session.commit()


def _record_report(session: Session, report_model, target: str, row, customer_id: str, reason: str) -> None:
    key = (row.id, customer_id)
    if row.status != "published" or row.customer_id == customer_id:
        raise not_found()
    if session.get(report_model, key):
        return
    session.add(report_model(**{target: row.id, "customer_id": customer_id, "reason_code": reason, "created_at": utc_now()}))
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        if not session.get(report_model, key):
            raise


def report_post(session: Session, customer_id: str, post_id: str, reason: str) -> None:
    row = _public_post(session, post_id, lock=True)
    _record_report(session, ShareReport, "share_id", row, customer_id, reason)


def report_reply(session: Session, customer_id: str, post_id: str, reply_id: str, reason: str) -> None:
    post = _visible_post(session, customer_id, post_id, lock=True)
    row = _reply_row(session, post, reply_id)
    _record_report(session, DiscussionReplyReport, "reply_id", row, customer_id, reason)


def reported_replies(session: Session) -> list[dict]:
    rows = session.execute(select(
        GroupShare.public_id, DiscussionReply.public_id, DiscussionReply.body,
        DiscussionReplyReport.reason_code, DiscussionReplyReport.created_at,
    ).join(DiscussionReply, DiscussionReply.share_id == GroupShare.id)
     .join(DiscussionReplyReport, DiscussionReplyReport.reply_id == DiscussionReply.id)
     .where(GroupShare.topic == "exercise", GroupShare.group_key == DISCUSSION_KEY,
            GroupShare.status == "published", DiscussionReply.status == "published")
     .order_by(DiscussionReplyReport.created_at.desc()).limit(50))
    return [{"post_id": post, "reply_id": reply, "body": body, "reason_code": reason, "reported_at": _iso(at)}
            for post, reply, body, reason, at in rows]


def hide_reply(session: Session, post_id: str, reply_id: str) -> None:
    row = _reply_row(session, _public_post(session, post_id, lock=True), reply_id)
    if row.status == "published":
        row.status = "hidden"
        session.commit()
