from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.errors import not_found
from app.db.session import get_session
from app.schemas.common import ApiResponse
from app.schemas.discussion import Category, DiscussionEditIn, DiscussionPostIn, DiscussionReplyIn, DiscussionSort, DiscussionView, ReactionKind, Scope
from app.schemas.wellness import ModerationIn, ReportIn
from app.services import exercise_discussion as discussion
from app.services.auth_service import CurrentUser

router = APIRouter(prefix="/herlog/exercise/discussion", tags=["exercise discussion"])
Db = Annotated[Session, Depends(get_session)]
User = Annotated[CurrentUser, Depends(get_current_user)]
Cursor = Annotated[int | None, Query(ge=1)]


@router.get("/posts")
def posts(db: Db, user: User, category: Category | None = None, cursor: Cursor = None,
          q: Annotated[str | None, Query(max_length=60)] = None, view: DiscussionView = "all",
          sort: DiscussionSort = "latest", scope: Scope = "all", cursor_likes: Annotated[int | None, Query(ge=0)] = None):
    return ApiResponse(data=discussion.list_posts(
        db, user.customer_id, category, cursor, q=q, view=scope if view == "all" else view, sort=sort, cursor_likes=cursor_likes,
    ))


@router.post("/posts")
def post(payload: DiscussionPostIn, db: Db, user: User):
    return ApiResponse(data=discussion.publish(db, user.customer_id, payload))


@router.put("/posts/{post_id}")
def edit(post_id: str, payload: DiscussionEditIn, db: Db, user: User):
    discussion.edit_post(db, user.customer_id, post_id, payload)
    return ApiResponse(data=None)


@router.put("/posts/{post_id}/reactions/{kind}")
def add_reaction(post_id: str, kind: ReactionKind, db: Db, user: User):
    return ApiResponse(data=discussion.set_reaction(db, user.customer_id, post_id, kind, True))


@router.delete("/posts/{post_id}/reactions/{kind}")
def remove_reaction(post_id: str, kind: ReactionKind, db: Db, user: User):
    return ApiResponse(data=discussion.set_reaction(db, user.customer_id, post_id, kind, False))


@router.delete("/posts/{post_id}")
def withdraw(post_id: str, db: Db, user: User):
    discussion.remove_post(db, user.customer_id, post_id)
    return ApiResponse(data=None)


@router.post("/posts/{post_id}/like")
def like(post_id: str, db: Db, user: User):
    return ApiResponse(data=discussion.toggle_like(db, user.customer_id, post_id, liked=True))


@router.delete("/posts/{post_id}/like")
def unlike(post_id: str, db: Db, user: User):
    return ApiResponse(data=discussion.toggle_like(db, user.customer_id, post_id, liked=False))


@router.get("/posts/{post_id}/images/{image_id}", response_class=Response)
def post_image(post_id: str, image_id: int, db: Db, user: User) -> Response:
    image = discussion.post_images(db, user.customer_id, post_id, image_id)
    return Response(image, media_type="image/jpeg", headers={
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
    })


@router.post("/posts/{post_id}/reports")
def report(post_id: str, payload: ReportIn, db: Db, user: User):
    discussion.report_post(db, user.customer_id, post_id, payload.reason_code)
    return ApiResponse(data=None)


@router.get("/posts/{post_id}/replies")
def replies(post_id: str, db: Db, user: User, cursor: Cursor = None):
    return ApiResponse(data=discussion.list_replies(db, user.customer_id, post_id, cursor))


@router.post("/posts/{post_id}/replies")
def reply(post_id: str, payload: DiscussionReplyIn, db: Db, user: User):
    return ApiResponse(data=discussion.reply(db, user.customer_id, post_id, payload))


@router.post("/posts/{post_id}/replies/{reply_id}/like")
def like_reply(post_id: str, reply_id: str, db: Db, user: User):
    return ApiResponse(data=discussion.toggle_reply_like(db, user.customer_id, post_id, reply_id, liked=True))


@router.delete("/posts/{post_id}/replies/{reply_id}/like")
def unlike_reply(post_id: str, reply_id: str, db: Db, user: User):
    return ApiResponse(data=discussion.toggle_reply_like(db, user.customer_id, post_id, reply_id, liked=False))


@router.delete("/posts/{post_id}/replies/{reply_id}")
def withdraw_reply(post_id: str, reply_id: str, db: Db, user: User):
    discussion.remove_reply(db, user.customer_id, post_id, reply_id)
    return ApiResponse(data=None)


@router.post("/posts/{post_id}/replies/{reply_id}/reports")
def report_reply(post_id: str, reply_id: str, payload: ReportIn, db: Db, user: User):
    discussion.report_reply(db, user.customer_id, post_id, reply_id, payload.reason_code)
    return ApiResponse(data=None)


@router.get("/moderation/reply-reports")
def reply_reports(db: Db, user: User):
    if user.customer_id != settings.HERLOG_GROUP_MODERATOR_ID:
        raise not_found()
    return ApiResponse(data=discussion.reported_replies(db))


@router.put("/posts/{post_id}/replies/{reply_id}/moderation")
def moderate_reply(post_id: str, reply_id: str, payload: ModerationIn, db: Db, user: User):
    if user.customer_id != settings.HERLOG_GROUP_MODERATOR_ID:
        raise not_found()
    if payload.action == "hide":
        discussion.hide_reply(db, post_id, reply_id)
    return ApiResponse(data=None)
