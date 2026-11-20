"""经验广场：官方种子帖 + 会员自由发帖 + 点赞去重。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.errors import forbidden, not_found
from app.models.herlog import Profile, WeightPost
from app.schemas.weight_plus import POST_TAGS, PostIn, PostOut, post_out

SEED_POSTS: tuple[tuple[str, str, str], ...] = (
    (
        "打卡",
        "第 3 周小结：每周 3 次力量 + 每天 8000 步，体重只掉了 1.2 kg，但腰带松了一格。数字慢一点没关系，衣服会说实话。",
        "她记编辑",
    ),
    (
        "饮食",
        "把外卖的酱汁单独装之后，同样一份饭少了两三百 kcal，吃饱感没变。先从最小的改起，比一下子戒断好坚持。",
        "她记编辑",
    ),
    (
        "心情",
        "记录断了两周又回来了。中断不算失败，重新开始的那天也算连续记录的第 1 天。",
        "她记编辑",
    ),
)


def _ensure_seed(session: Session) -> None:
    existing = session.scalar(
        select(func.count()).select_from(WeightPost).where(WeightPost.official.is_(True))
    )
    if existing:
        return
    now = utc_now()
    for tag, body, nickname in SEED_POSTS:
        session.add(
            WeightPost(
                customer_id=None,
                nickname=nickname,
                tag=tag,
                body=body,
                like_count=0,
                liked_by=[],
                official=True,
                created_at=now,
            )
        )
    session.commit()


def list_posts(session: Session, customer_id: str, tag: str | None = None) -> list[PostOut]:
    _ensure_seed(session)
    conditions = [WeightPost.tag == tag] if tag else []
    rows = session.scalars(
        select(WeightPost)
        .where(*conditions)
        .order_by(WeightPost.official.desc(), WeightPost.created_at.desc(), WeightPost.id.desc())
        .limit(50)
    ).all()
    return [post_out(row, customer_id) for row in rows]


def _nickname(session: Session, customer_id: str) -> str:
    profile = session.get(Profile, customer_id)
    if profile is not None and profile.username:
        return profile.username[:32]
    return "她记用户"


def create_post(session: Session, customer_id: str, payload: PostIn) -> PostOut:
    row = WeightPost(
        customer_id=customer_id,
        nickname=_nickname(session, customer_id),
        tag=payload.tag,
        body=payload.body,
        like_count=0,
        liked_by=[],
        official=False,
        created_at=utc_now(),
    )
    session.add(row)
    session.commit()
    return post_out(row, customer_id)


def toggle_like(session: Session, customer_id: str, post_id: int) -> PostOut:
    row = session.scalar(select(WeightPost).where(WeightPost.id == post_id))
    if row is None:
        raise not_found()
    liked_by = list(row.liked_by or [])
    if customer_id in liked_by:
        liked_by.remove(customer_id)
    else:
        liked_by.append(customer_id)
    row.liked_by = liked_by
    row.like_count = len(liked_by)
    session.commit()
    return post_out(row, customer_id)


def delete_post(session: Session, customer_id: str, post_id: int) -> None:
    row = session.scalar(select(WeightPost).where(WeightPost.id == post_id))
    if row is None:
        raise not_found()
    if row.customer_id != customer_id:
        raise forbidden("只能删除自己发布的经验")
    session.delete(row)
    session.commit()


def available_tags() -> tuple[str, ...]:
    return POST_TAGS
