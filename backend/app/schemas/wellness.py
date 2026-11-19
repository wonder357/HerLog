from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.private_photo import PrivatePhotoIn

Topic = Literal["exercise", "skin"]
GroupKey = Literal["general", "menstrual", "follicular", "ovulatory", "luteal"]
ActivityCode = Literal["walk", "mobility", "strength", "cycle", "rest", "yoga", "jog", "swim", "dance"]
SkinType = Literal["dry", "oily", "combination", "balanced", "unsure"]
SkinSensation = Literal["tight", "shine", "sensitive", "rough", "redness"]
SkinRoutine = Literal["cleanse", "moisturize", "sunscreen", "shade", "cover", "reapply"]
CaptionCode = Literal["checked_in", "kept_it_light", "made_time", "care_routine", "sun_care", "reflection"]


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CheckinUpdate(StrictInput):
    activity_code: ActivityCode
    started_at: datetime
    duration_minutes: int | None = Field(default=None, ge=1, le=1440, strict=True)
    effort: Literal["easy", "moderate", "hard"] | None = None
    feeling_code: Literal["comfortable", "tired", "energetic"] | None = None
    photo: PrivatePhotoIn | None = None

    @field_validator("started_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("请提供带时区的发生时间")
        return value

    @model_validator(mode="after")
    def validate_rest(self):
        if self.activity_code == "rest" and (self.duration_minutes is not None or self.effort is not None):
            raise ValueError("休息记录无需填写时长和运动强度")
        return self


class CheckinIn(CheckinUpdate):
    client_key: str = Field(min_length=8, max_length=36)


class SkinJournalIn(StrictInput):
    skin_type: SkinType | None = None
    comfort: int | None = Field(default=None, ge=1, le=5, strict=True)
    sensations: list[SkinSensation] = Field(default_factory=list, max_length=5)
    routine: list[SkinRoutine] = Field(default_factory=list, max_length=6)
    note: str | None = Field(default=None, max_length=400)


class SkinJournalOut(SkinJournalIn):
    day: date


class JoinGroupIn(StrictInput):
    invite_code: str = Field(min_length=1, max_length=64)
    consent: Literal[True]


class ShareIn(StrictInput):
    group_key: GroupKey
    client_key: str = Field(min_length=8, max_length=36)
    checkin_id: int | None = Field(default=None, gt=0)
    day: date | None = None
    caption_code: CaptionCode
    include_duration_bucket: bool = False


class ReportIn(StrictInput):
    reason_code: Literal["comparison", "body_shaming", "restriction", "personal_info", "other"]


class ReplyIn(StrictInput):
    reply_code: Literal["also_record", "thanks", "keep_observing"]


class ModerationIn(StrictInput):
    action: Literal["hide"]
