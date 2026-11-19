from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.private_photo import PrivatePhotoIn

SITES = ("面部", "额头", "下巴", "脸颊", "颈部", "背部", "胸口", "手臂", "其他")
SKIN_MIME_TYPES = ("image/jpeg", "image/png")
FLOWS = ("少量", "中等", "较多")
SYMPTOMS = ("腹痛", "腹胀", "头痛", "疲惫", "情绪变化", "腰酸", "恶心", "乳房胀痛")
IMPACTS = ("无影响", "轻微影响", "影响日常", "影响睡眠")
Mood = Literal["轻松", "平静", "烦躁", "低落", "紧张"]


def _as_utc_iso(moment: datetime) -> str:
    """库内存 UTC naive；对外统一输出带 Z 的 ISO 时间，由前端换成本地时间。"""

    return moment.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _require_aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        raise ValueError("时间需带时区，例如 2026-11-18T08:00:00+08:00")
    return moment


class ProfileOut(BaseModel):
    username: str
    birthday: date | None = None
    height_cm: Decimal | None = None
    contact_phone: str | None = None
    has_avatar: bool = False


class ProfileUpdate(BaseModel):
    birthday: date | None = None
    height_cm: Decimal | None = Field(default=None, decimal_places=2)
    contact_phone: str | None = Field(default=None, max_length=32)
    avatar: PrivatePhotoIn | None = None

    @field_validator("height_cm")
    @classmethod
    def check_height(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("身高需为正数")
        if value > Decimal("999.99"):
            raise ValueError("身高超出可用范围")
        return value

    @field_validator("birthday")
    @classmethod
    def check_birthday(cls, value: date | None) -> date | None:
        from app.core.clock import local_today

        if value is not None and value > local_today():
            raise ValueError("生日不能晚于今天")
        return value

    @field_validator("contact_phone")
    @classmethod
    def blank_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class PeriodIn(BaseModel):
    start_day: date
    end_day: date | None = None

    @model_validator(mode="after")
    def check_order(self) -> "PeriodIn":
        if self.end_day is not None and self.end_day < self.start_day:
            raise ValueError("结束日期不能早于开始日期")
        return self


class PeriodOut(BaseModel):
    id: int
    start_day: date
    end_day: date | None = None
    duration_days: int | None = None
    cycle_days: int | None = None


class FeelingIn(BaseModel):
    flow: str | None = None
    mood: Mood | None = None
    symptoms: list[str] = Field(default_factory=list, max_length=8)
    impact: str | None = None
    note: str | None = Field(default=None, max_length=500)

    @field_validator("flow")
    @classmethod
    def check_flow(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        if value not in FLOWS:
            raise ValueError(f"经量只能是：{'、'.join(FLOWS)}")
        return value

    @field_validator("symptoms")
    @classmethod
    def check_symptoms(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            if item not in SYMPTOMS:
                raise ValueError(f"未知的症状：{item}")
            if item not in cleaned:
                cleaned.append(item)
        return cleaned

    @field_validator("impact")
    @classmethod
    def check_impact(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        if value not in IMPACTS:
            raise ValueError(f"生活影响只能是：{'、'.join(IMPACTS)}")
        return value

    @field_validator("note")
    @classmethod
    def blank_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class FeelingOut(BaseModel):
    day: date
    flow: str | None = None
    mood: Mood | None = None
    symptoms: list[str] = Field(default_factory=list)
    impact: str | None = None
    note: str | None = None


WeightFeeling = Literal["bloating", "puffy", "tired", "comfortable"]


class WeightIn(BaseModel):
    client_key: str = Field(min_length=8, max_length=36)
    kg: Decimal
    measured_at: datetime
    tag: str | None = Field(default=None, max_length=32)
    note: str | None = Field(default=None, max_length=500)
    feeling_tags: list[WeightFeeling] | None = Field(default=None, max_length=3)
    photo: PrivatePhotoIn | None = None

    @field_validator("measured_at")
    @classmethod
    def check_measured_at(cls, value: datetime) -> datetime:
        return _require_aware(value)

    @field_validator("kg")
    @classmethod
    def check_kg(cls, value: Decimal) -> Decimal:
        try:
            exponent = value.as_tuple().exponent
        except (InvalidOperation, AttributeError) as exc:  # pragma: no cover - 防御
            raise ValueError("体重格式不正确") from exc
        if not isinstance(exponent, int) or exponent < -3:
            raise ValueError("体重最多三位小数")
        if value <= 0:
            raise ValueError("体重需为正数")
        return value

    @field_validator("tag")
    @classmethod
    def blank_tag(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class WeightOut(BaseModel):
    id: int
    client_key: str
    grams: int
    kg: float
    measured_at: str
    tag: str | None = None
    note: str | None = None
    feeling_tags: list[WeightFeeling] = Field(default_factory=list)
    source: Literal["manual", "scale"] = "manual"
    device_id: int | None = None
    has_photo: bool = False


class WeightPointOut(BaseModel):
    day: date
    grams: int
    kg: float
    weight_id: int
    measured_at: str


class MetricSlot(BaseModel):
    value: float | None = None
    unit: str
    status: Literal["available", "missing_height", "not_connected", "no_data", "unsupported"]
    source: str | None = None
    measured_at: str | None = None


class CycleDayOut(BaseModel):
    day: date
    phase: Literal["menstrual", "follicular", "ovulatory", "luteal", "unknown"]
    basis: Literal["recorded", "estimated", "unknown"]
    note: str | None = None


class WeightSummaryOut(BaseModel):
    days: int
    latest_grams: int | None = None
    latest_kg: float | None = None
    latest_measured_at: str | None = None
    count: int
    points: list[WeightPointOut] = Field(default_factory=list)
    delta_grams: int | None = None
    delta_kg: float | None = None
    suggestion: str | None = None
    latest_record_id: int | None = None
    record_days: int = 0
    metrics: dict[str, MetricSlot] = Field(default_factory=dict)
    cycle_context: list[CycleDayOut] | None = None


class WeightListOut(BaseModel):
    items: list[WeightOut] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class SkinAnalyzeIn(BaseModel):
    site: str = Field(min_length=1, max_length=40)
    captured_at: datetime
    mime: Literal["image/jpeg", "image/png"]
    image_base64: str = Field(min_length=32)

    @field_validator("site")
    @classmethod
    def check_site(cls, value: str) -> str:
        if value not in SITES:
            raise ValueError(f"部位需在：{'、'.join(SITES)}")
        return value

    @field_validator("captured_at")
    @classmethod
    def check_captured_at(cls, value: datetime) -> datetime:
        return _require_aware(value)


class SkinQualityOut(BaseModel):
    level: Literal["good", "limited"]
    message: str


class SkinAnalysisOut(BaseModel):
    analysis_id: str
    expires_at: str
    site: str
    captured_at: str
    quality: SkinQualityOut
    visible: str
    unclear: str
    attention: str
    model_id: str
    prompt_version: str
    demo_sample: bool = False
    inference_ms: int | None = None


class SkinSaveIn(BaseModel):
    analysis_id: str = Field(min_length=8, max_length=36)


class SkinObservationOut(BaseModel):
    id: int
    site: str
    captured_at: str
    mime: str
    visible: str
    unclear: str
    attention: str
    model_id: str
    prompt_version: str
    has_image: bool = True
    quality: SkinQualityOut | None = None
    demo_sample: bool = False


class SkinSummaryOut(BaseModel):
    id: int
    site: str
    captured_at: str
    visible: str
    demo_sample: bool = False


AssistantTopic = Literal["weight", "period", "skin"]


class AssistantQueryIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    follow_up_topic: AssistantTopic | None = None

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("问题不能为空")
        return stripped


class RecordRef(BaseModel):
    type: Literal["weight", "period", "feeling", "skin", "profile"]
    id: str
    label: str
    route: str


class AssistantRange(BaseModel):
    label: str
    date_from: date | None = None
    date_to: date | None = None
    days: int | None = None


class AssistantAnswerOut(BaseModel):
    answer: str
    domain: Literal["weight", "period", "skin", "record_help", "unsupported"]
    range: AssistantRange
    record_refs: list[RecordRef] = Field(default_factory=list)
    model_id: str | None = None


def weight_out(row: Any, has_photo: bool = False) -> WeightOut:
    return WeightOut(
        id=row.id,
        client_key=row.client_key,
        grams=row.grams,
        kg=round(row.grams / 1000, 3),
        measured_at=_as_utc_iso(row.measured_at),
        tag=row.tag,
        note=row.note,
        feeling_tags=row.feeling_tags or [],
        source=row.source,
        device_id=row.device_id,
        has_photo=has_photo,
    )
