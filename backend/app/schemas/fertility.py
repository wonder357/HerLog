from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

CycleMode = Literal["period", "trying_to_conceive"]
LHResult = Literal["negative", "weak_positive", "strong_positive"]
Mucus = Literal["dry", "sticky", "creamy", "watery", "stretchy", "unsure"]
Temperature = Annotated[Decimal, Field(ge=Decimal("30.00"), le=Decimal("45.00"), decimal_places=2)]


class ModeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    active_mode: CycleMode


class StartDateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trying_started_on: date | None


class PreferenceOut(BaseModel):
    active_mode: CycleMode = "period"
    configured: bool = False
    seen_fertility: bool = False
    trying_started_on: date | None = None


class LHTest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result: LHResult
    measured_at: AwareDatetime | None = None


class DailyValues(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bbt_c: Temperature | None = None
    bbt_measured_at: AwareDatetime | None = None
    lh_tests: list[LHTest] = Field(default_factory=list, max_length=8)
    cervical_mucus: Mucus | None = None
    intercourse_occurred: bool | None = Field(default=None, strict=True)


class DailyIn(DailyValues):
    expected_revision: UUID | None

    @field_validator("bbt_c", mode="before")
    @classmethod
    def parse_temperature(cls, value: object) -> object:
        if value is not None and (not isinstance(value, str) or not re.fullmatch(r"[0-9]{2}(\.[0-9]{1,2})?", value)):
            raise ValueError("体温请填写摄氏度，最多两位小数")
        return value

    @model_validator(mode="after")
    def check_content(self) -> DailyIn:
        if self.bbt_c is None and self.bbt_measured_at is not None:
            raise ValueError("填写测量时间前请先填写体温")
        if self.bbt_c is None and not self.lh_tests and self.cervical_mucus is None and self.intercourse_occurred is None:
            raise ValueError("请至少填写一项观察")
        times = [test.measured_at for test in self.lh_tests]
        if len(set(times)) != len(times):
            raise ValueError("每个时刻只能保存一笔试纸结果，时间未记录也只保留一笔")
        return self


class DailyOut(DailyValues):
    day: date
    revision: UUID
    updated_at: datetime
