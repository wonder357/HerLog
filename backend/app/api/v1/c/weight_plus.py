"""体重 tag 的扩展接口：目标、对比、饮食、教练、知识库、经验广场。

注意：本路由必须在 `weights.router` 之前注册，否则 `PUT /herlog/weights/goal`
会被 `PUT /herlog/weights/{weight_id}` 先匹配到。
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import not_found
from app.db.session import get_session
from app.schemas.common import ApiResponse
from app.schemas.weight_plus import (
    AnalyzeIn,
    CoachChatIn,
    CoachChatOut,
    CoachReportOut,
    CompareOut,
    DailyNutritionOut,
    GoalIn,
    GoalOut,
    KnowledgeDetailOut,
    KnowledgeTopicOut,
    MealEstimateOut,
    MealIn,
    MealOut,
    PostIn,
    PostOut,
)
from app.services import coach_service, goal_service, knowledge, meal_service, post_service
from app.services.auth_service import CurrentUser
from app.services.weight_service import compare

router = APIRouter(prefix="/herlog", tags=["herlog-weight"])


@router.get("/weights/goal", response_model=ApiResponse[GoalOut])
def read_goal(
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user)
) -> ApiResponse[GoalOut]:
    return ApiResponse(data=goal_service.goal_state(session, user.customer_id))


@router.put("/weights/goal", response_model=ApiResponse[GoalOut])
def write_goal(
    payload: GoalIn,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[GoalOut]:
    return ApiResponse(data=goal_service.set_goal(session, user.customer_id, payload))


@router.delete("/weights/goal", response_model=ApiResponse[GoalOut])
def drop_goal(
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user)
) -> ApiResponse[GoalOut]:
    return ApiResponse(data=goal_service.clear_goal(session, user.customer_id))


@router.get("/weights/compare", response_model=ApiResponse[CompareOut])
def weight_compare(
    days: int = Query(default=7, description="只支持 7 或 30"),
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[CompareOut]:
    return ApiResponse(data=compare(session, user.customer_id, days))


@router.get("/nutrition/daily", response_model=ApiResponse[DailyNutritionOut])
def read_daily(
    day: date | None = None,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[DailyNutritionOut]:
    return ApiResponse(data=meal_service.daily(session, user.customer_id, day))


@router.post("/nutrition/analyze", response_model=ApiResponse[MealEstimateOut])
def analyze_meal(
    payload: AnalyzeIn, user: CurrentUser = Depends(get_current_user)
) -> ApiResponse[MealEstimateOut]:
    return ApiResponse(data=meal_service.analyze(payload.text))


@router.post("/nutrition/meals", response_model=ApiResponse[MealOut])
def create_meal(
    payload: MealIn,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[MealOut]:
    record, _created = meal_service.create_meal(session, user.customer_id, payload)
    return ApiResponse(data=record)


@router.delete("/nutrition/meals/{meal_id}", response_model=ApiResponse[None])
def delete_meal(
    meal_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[None]:
    meal_service.delete_meal(session, user.customer_id, meal_id)
    return ApiResponse(data=None)


@router.post("/coach/report", response_model=ApiResponse[CoachReportOut])
def coach_report(
    days: int = Query(default=7, description="只支持 7 或 30"),
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[CoachReportOut]:
    return ApiResponse(data=coach_service.report(session, user.customer_id, days))


@router.post("/coach/chat", response_model=ApiResponse[CoachChatOut])
def coach_chat(
    payload: CoachChatIn,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[CoachChatOut]:
    return ApiResponse(data=coach_service.chat(session, user.customer_id, payload.question))


@router.get("/knowledge", response_model=ApiResponse[list[KnowledgeTopicOut]])
def list_knowledge(
    tag: str | None = None, user: CurrentUser = Depends(get_current_user)
) -> ApiResponse[list[KnowledgeTopicOut]]:
    rows = [
        KnowledgeTopicOut(
            slug=topic.slug,
            title=topic.title,
            tag=topic.tag,
            summary=topic.summary,
            source=topic.source,
            minutes=topic.minutes,
        )
        for topic in knowledge.list_topics(tag)
    ]
    return ApiResponse(data=rows)


@router.get("/knowledge/{slug}", response_model=ApiResponse[KnowledgeDetailOut])
def read_knowledge(
    slug: str, user: CurrentUser = Depends(get_current_user)
) -> ApiResponse[KnowledgeDetailOut]:
    topic = knowledge.get_topic(slug)
    if topic is None:
        raise not_found("没有这篇科普")
    return ApiResponse(
        data=KnowledgeDetailOut(
            slug=topic.slug,
            title=topic.title,
            tag=topic.tag,
            summary=topic.summary,
            source=topic.source,
            minutes=topic.minutes,
            body=list(topic.body),
        )
    )


@router.get("/community/posts", response_model=ApiResponse[list[PostOut]])
def list_posts(
    tag: str | None = None,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[list[PostOut]]:
    return ApiResponse(data=post_service.list_posts(session, user.customer_id, tag))


@router.post("/community/posts", response_model=ApiResponse[PostOut])
def create_post(
    payload: PostIn,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[PostOut]:
    return ApiResponse(data=post_service.create_post(session, user.customer_id, payload))


@router.post("/community/posts/{post_id}/like", response_model=ApiResponse[PostOut])
def like_post(
    post_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[PostOut]:
    return ApiResponse(data=post_service.toggle_like(session, user.customer_id, post_id))


@router.delete("/community/posts/{post_id}", response_model=ApiResponse[None])
def delete_post(
    post_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[None]:
    post_service.delete_post(session, user.customer_id, post_id)
    return ApiResponse(data=None)
