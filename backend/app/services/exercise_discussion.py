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
from app.models.herlog import Profile
from app.models.wellness import (
    DiscussionImage, DiscussionLike, DiscussionReply, DiscussionReplyLike, DiscussionReplyReport, GroupShare,
    DiscussionReaction, ShareReport,
)
from app.schemas.discussion import DiscussionEditIn, DiscussionPostIn, DiscussionReplyIn
from app.services import private_photo
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


def _display_name(session: Session, customer_id: str) -> str:
    profile = session.get(Profile, customer_id)
    if profile is not None and profile.username:
        return profile.username[:32]
    return "她记用户"


def _snapshot(payload: DiscussionPostIn, author: str | None, activity: str | None) -> dict:
    snapshot = {
        "category": payload.category, "title": payload.title, "body": payload.body,
        "visibility": payload.visibility, "author": author,
    }
    if activity:
        snapshot["activity"] = activity
    return snapshot


def _post_out(post: GroupShare, customer_id: str, reply_count: int = 0, like_count: int = 0,
              liked: bool = False, image_ids: list[int] | None = None, saved: bool = False) -> dict:
    anonymous = post.snapshot.get("visibility", "anonymous") != "public"
    return {
        "public_id": post.public_id, "category": post.snapshot["category"], "title": post.snapshot["title"],
        "body": post.snapshot["body"], "activity": post.snapshot.get("activity"),
        "visibility": "anonymous" if anonymous else "public",
        "author": None if anonymous else post.snapshot.get("author"),
        "published_at": _iso(post.published_at), "mine": post.customer_id == customer_id,
        "reply_count": reply_count, "like_count": like_count, "liked": liked,
        "image_ids": image_ids or [], "saved": saved,
    }


def _reply_out(row: DiscussionReply, customer_id: str, like_count: int = 0, liked: bool = False) -> dict:
    anonymous = (row.visibility or "anonymous") != "public"
    return {
        "public_id": row.public_id, "body": row.body, "published_at": _iso(row.published_at),
        "mine": row.customer_id == customer_id,
        "visibility": "anonymous" if anonymous else "public",
        "author": None if anonymous else row.author,
        "like_count": like_count, "liked": liked,
    }


def _visible_replies(customer_id: str):
    return (
        DiscussionReply.status == "published",
        ~select(DiscussionReplyReport.reply_id).where(
            DiscussionReplyReport.reply_id == DiscussionReply.id,
            DiscussionReplyReport.customer_id == customer_id,
        ).exists(),
    )


def _count_map(session: Session, column, model, ids: list[int]) -> dict[int, int]:
    if not ids:
        return {}
    return dict(session.execute(
        select(column, func.count()).where(column.in_(ids)).group_by(column)
    ).all())


def _liked_ids(session: Session, column, model, ids: list[int], customer_id: str) -> set[int]:
    if not ids:
        return set()
    return set(session.scalars(select(column).where(column.in_(ids), model.customer_id == customer_id)))


def _image_ids(session: Session, share_ids: list[int]) -> dict[int, list[int]]:
    if not share_ids:
        return {}
    grouped: dict[int, list[int]] = {}
    for share_id, image_id in session.execute(
        select(DiscussionImage.share_id, DiscussionImage.id)
        .where(DiscussionImage.share_id.in_(share_ids))
        .order_by(DiscussionImage.share_id, DiscussionImage.position)
    ):
        grouped.setdefault(share_id, []).append(image_id)
    return grouped


def _like_count():
    return select(func.count()).select_from(DiscussionLike).where(
        DiscussionLike.share_id == GroupShare.id,
    ).correlate(GroupShare).scalar_subquery()


def _reaction_states(session: Session, customer_id: str, ids: list[int]) -> dict[int, dict]:
    likes = _count_map(session, DiscussionLike.share_id, DiscussionLike, ids)
    liked = _liked_ids(session, DiscussionLike.share_id, DiscussionLike, ids, customer_id)
    saved = set(session.scalars(select(DiscussionReaction.share_id).where(
        DiscussionReaction.share_id.in_(ids), DiscussionReaction.customer_id == customer_id,
        DiscussionReaction.kind == "save",
    ))) if ids else set()
    return {post_id: {"like_count": likes.get(post_id, 0), "liked": post_id in liked, "saved": post_id in saved}
            for post_id in ids}


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
            if cursor_likes is not None:
                query = query.where(or_(likes < cursor_likes, (likes == cursor_likes) & (GroupShare.id < cursor)))
            else:
                query = query.offset(cursor)
        query = query.add_columns(likes.label("rank_likes")).order_by(likes.desc())
    elif cursor is not None:
        query = query.where(GroupShare.id < cursor)
    rows = session.execute(query.order_by(GroupShare.id.desc()).limit(PAGE_SIZE + 1)).all()
    page = [result[0] for result in rows[:PAGE_SIZE]]
    ids = [row.id for row in page]
    states = _reaction_states(session, customer_id, ids)
    images = _image_ids(session, ids)
    counts = dict(session.execute(
        select(DiscussionReply.share_id, func.count()).where(
            DiscussionReply.share_id.in_(ids), *_visible_replies(customer_id),
        ).group_by(DiscussionReply.share_id),
    ).all()) if page else {}
    result = {
        "items": [_post_out(row, customer_id, counts.get(row.id, 0), image_ids=images.get(row.id), **states[row.id]) for row in page],
        "next_cursor": page[-1].id if len(rows) > PAGE_SIZE else None,
    }
    if sort == "popular" and len(rows) > PAGE_SIZE:
        result["next_cursor_likes"] = rows[PAGE_SIZE - 1].rank_likes
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
    if kind == "like":
        state = toggle_like(session, customer_id, post_id, liked=enabled)
        return {**state, "saved": session.get(DiscussionReaction, (post.id, "save", customer_id)) is not None}
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
    prepared = [private_photo.prepare(image) for image in payload.images]
    digests = [photo.digest for photo in prepared if photo is not None]
    post_id = uuid4().hex
    author = _display_name(session, customer_id) if payload.visibility == "public" else None
    activity = None
    if payload.checkin_id is not None:
        entry = member_checkin(session, customer_id, payload.checkin_id, lock=True)
        activity = ACTIVITIES[entry.activity_code][0]
    snapshot = _snapshot(payload, author, activity)
    reference = str(payload.checkin_id) if payload.checkin_id is not None else post_id
    original = session.scalar(_public_posts().where(
        GroupShare.customer_id == customer_id, GroupShare.client_key == payload.client_key,
    ).with_for_update())
    if original is not None:
        if original.status != "published" or (original.snapshot | {"visibility": original.snapshot.get("visibility", "anonymous"),
            "author": original.snapshot.get("author")}) != snapshot or (
            payload.checkin_id is not None and original.reference_key != reference
        ) or sorted(_stored_digests(session, original.id)) != sorted(digests):
            raise conflict("这次请求已用于另一条讨论，请重新发布")
        return _post_out(original, customer_id, image_ids=_image_ids(session, [original.id]).get(original.id, []))

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
        session.flush()
        for position, photo in enumerate(prepared):
            if photo is None:
                continue
            session.add(DiscussionImage(share_id=row.id, position=position, image_bytes=photo.data,
                                        digest=photo.digest))
        session.commit()
    except IntegrityError:
        session.rollback()
        original = session.scalar(_public_posts().where(
            GroupShare.customer_id == customer_id, GroupShare.client_key == payload.client_key,
        ))
        if original is not None and original.status == "published" and (original.snapshot | {"visibility": original.snapshot.get("visibility", "anonymous"),
            "author": original.snapshot.get("author")}) == snapshot and (
            payload.checkin_id is None or original.reference_key == reference
        ) and sorted(_stored_digests(session, original.id)) == sorted(digests):
            return _post_out(original, customer_id,
                             image_ids=_image_ids(session, [original.id]).get(original.id, []))
        raise conflict("该打卡已有公开讨论，或发布请求已使用")
    return _post_out(row, customer_id, image_ids=_image_ids(session, [row.id]).get(row.id, []))


def _stored_digests(session: Session, share_id: int) -> list[str]:
    return list(session.scalars(
        select(DiscussionImage.digest).where(DiscussionImage.share_id == share_id)
        .order_by(DiscussionImage.position)
    ))


def post_images(session: Session, customer_id: str, post_id: str, image_id: int):
    post = _visible_post(session, customer_id, post_id)
    image = session.scalar(
        select(DiscussionImage.image_bytes).where(
            DiscussionImage.id == image_id, DiscussionImage.share_id == post.id,
        )
    )
    if image is None:
        raise not_found()
    return image


def toggle_like(session: Session, customer_id: str, post_id: str, *, liked: bool) -> dict:
    post = _visible_post(session, customer_id, post_id, lock=True)
    existing = session.get(DiscussionLike, (post.id, customer_id))
    if liked and existing is None:
        session.add(DiscussionLike(share_id=post.id, customer_id=customer_id, created_at=utc_now()))
    elif not liked and existing is not None:
        session.delete(existing)
    try:
        session.commit()
    except IntegrityError:
        # 并发点赞：另一请求已写入，结果等价。
        session.rollback()
    total = session.scalar(
        select(func.count()).select_from(DiscussionLike).where(DiscussionLike.share_id == post.id)
    ) or 0
    return {"liked": liked, "like_count": total}


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
    page = rows[:PAGE_SIZE]
    ids = [row.id for row in page]
    likes = _count_map(session, DiscussionReplyLike.reply_id, DiscussionReplyLike, ids)
    mine_liked = _liked_ids(session, DiscussionReplyLike.reply_id, DiscussionReplyLike, ids, customer_id)
    return {
        "items": [_reply_out(row, customer_id, likes.get(row.id, 0), row.id in mine_liked) for row in page],
        "next_cursor": rows[PAGE_SIZE - 1].id if len(rows) > PAGE_SIZE else None,
    }


def reply(session: Session, customer_id: str, post_id: str, payload: DiscussionReplyIn) -> dict:
    _check_text(payload.body)
    post = _visible_post(session, customer_id, post_id, lock=True)
    row = DiscussionReply(
        public_id=uuid4().hex, share_id=post.id, customer_id=customer_id,
        body=payload.body, client_key=payload.client_key, published_at=utc_now(), status="published",
        visibility=payload.visibility,
        author=_display_name(session, customer_id) if payload.visibility == "public" else None,
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


def toggle_reply_like(session: Session, customer_id: str, post_id: str, reply_id: str, *, liked: bool) -> dict:
    post = _visible_post(session, customer_id, post_id, lock=True)
    row = _reply_row(session, post, reply_id)
    if row.status != "published":
        raise not_found()
    existing = session.get(DiscussionReplyLike, (row.id, customer_id))
    if liked and existing is None:
        session.add(DiscussionReplyLike(reply_id=row.id, customer_id=customer_id, created_at=utc_now()))
    elif not liked and existing is not None:
        session.delete(existing)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
    total = session.scalar(
        select(func.count()).select_from(DiscussionReplyLike).where(DiscussionReplyLike.reply_id == row.id)
    ) or 0
    return {"liked": liked, "like_count": total}


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
