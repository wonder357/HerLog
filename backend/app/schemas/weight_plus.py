"""体重 tag 扩展接口的出入参：目标、饮食、对比、教练、知识库、经验广场。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.logic.nutrition import MEAL_TYPES
from app.schemas.herlog import _as_utc_iso, _require_aware

GOAL_RATE_LIMITS = (Decimal("0.1"), Decimal("1.5"))


class GoalIn(BaseModel):
    target_kg: Decimal
    weekly_rate_kg: Decimal = Decimal("0.5")

    @field_validator("target_kg")
    @classmethod
    def check_target(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("目标体重需为正数")
        if value > Decimal("999.99"):
            raise ValueError("目标体重超出可用范围")
        return value

    @field_validator("weekly_rate_kg")
    @classmethod
    def check_rate(cls, value: Decimal) -> Decimal:
        low, high = GOAL_RATE_LIMITS
        if value < low or value > high:
            raise ValueError(f"每周减重速度需在 {low}~{high} kg 之间")
        return value


class BmiOut(BaseModel):
    value: float | None = None
    category: str
    advice: str


class GoalOut(BaseModel):
    has_goal: bool
    target_kg: float | None = None
    start_kg: float | None = None
    start_day: str | None = None
    weekly_rate_kg: float | None = None
    percent: float = 0.0
    remaining_kg: float | None = None
    reached: bool = False
    message: str = ""
    forecast_day: str | None = None
    slope_kg_per_week: float | None = None
    bmr_kcal: int | None = None
    tdee_kcal: int | None = None
    intake_target_kcal: int | None = None
    bmi: BmiOut


class CompareWindowOut(BaseModel):
    start_day: date
    end_day: date
    days: int
    count: int
    coverage_days: int
    first_kg: float | None = None
    last_kg: float | None = None
    avg_kg: float | None = None
    delta_kg: float | None = None


class CompareOut(BaseModel):
    days: int
    current: CompareWindowOut
    previous: CompareWindowOut
    avg_delta_kg: float | None = None
    message: str


class MealIn(BaseModel):
    client_key: str = Field(min_length=8, max_length=36)
    text: str = Field(min_length=1, max_length=500)
    meal_type: str = "加餐"
    eaten_at: datetime

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("写一句吃了什么")
        return stripped

    @field_validator("meal_type")
    @classmethod
    def check_meal_type(cls, value: str) -> str:
        if value not in MEAL_TYPES:
            raise ValueError(f"餐次只能是：{'、'.join(MEAL_TYPES)}")
        return value

    @field_validator("eaten_at")
    @classmethod
    def check_eaten_at(cls, value: datetime) -> datetime:
        return _require_aware(value)


class AnalyzeIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("写一句吃了什么")
        return stripped


class EstimateItemOut(BaseModel):
    name: str
    portion: str
    kcal: int
    protein_g: int
    carb_g: int
    fat_g: int


class MealEstimateOut(BaseModel):
    items: list[EstimateItemOut] = Field(default_factory=list)
    kcal: int
    protein_g: int
    carb_g: int
    fat_g: int
    confidence: Literal["none", "medium", "high"]
    note: str
    demo_sample: bool = False


class MealOut(BaseModel):
    id: int
    client_key: str
    text: str
    meal_type: str
    eaten_at: str
    kcal: int
    protein_g: int
    carb_g: int
    fat_g: int
    estimate_source: str


class MacroOut(BaseModel):
    carb: float
    protein: float
    fat: float


class DailyNutritionOut(BaseModel):
    day: str
    target_kcal: int | None = None
    intake_kcal: int
    remaining_kcal: int | None = None
    macros: MacroOut
    meals: list[MealOut] = Field(default_factory=list)
    message: str


class CoachReportOut(BaseModel):
    range_label: str
    summary: str
    highlights: list[str] = Field(default_factory=list)
    cautions: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    model_id: str
    demo_sample: bool = False


class CoachChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=300)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("问题不能为空")
        return stripped


class KnowledgeRefOut(BaseModel):
    slug: str
    title: str


class CoachChatOut(BaseModel):
    answer: str
    facts: list[str] = Field(default_factory=list)
    knowledge: list[KnowledgeRefOut] = Field(default_factory=list)
    model_id: str
    demo_sample: bool = False


class KnowledgeTopicOut(BaseModel):
    slug: str
    title: str
    tag: str
    summary: str
    source: str
    minutes: int


class KnowledgeDetailOut(KnowledgeTopicOut):
    body: list[str] = Field(default_factory=list)


POST_TAGS = ("减脂", "健身", "饮食", "心情", "打卡")


class PostIn(BaseModel):
    tag: str = "打卡"
    body: str = Field(min_length=4, max_length=500)

    @field_validator("tag")
    @classmethod
    def check_tag(cls, value: str) -> str:
        if value not in POST_TAGS:
            raise ValueError(f"话题只能是：{'、'.join(POST_TAGS)}")
        return value

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 4:
            raise ValueError("至少写 4 个字")
        return stripped


class PostOut(BaseModel):
    id: int
    nickname: str
    tag: str
    like_count: int
    liked: bool
    official: bool
    mine: bool
    created_at: str
    body: str


def meal_out(row) -> MealOut:
    return MealOut(
        id=row.id,
        client_key=row.client_key,
        text=row.text,
        meal_type=row.meal_type,
        eaten_at=_as_utc_iso(row.eaten_at),
        kcal=row.kcal,
        protein_g=row.protein_g,
        carb_g=row.carb_g,
        fat_g=row.fat_g,
        estimate_source=row.estimate_source,
    )


def post_out(row, viewer_id: str) -> PostOut:
    liked_by = list(row.liked_by or [])
    return PostOut(
        id=row.id,
        nickname=row.nickname,
        tag=row.tag,
        like_count=row.like_count,
        liked=viewer_id in liked_by,
        official=row.official,
        mine=row.customer_id == viewer_id,
        created_at=_as_utc_iso(row.created_at),
        body=row.body,
    )
