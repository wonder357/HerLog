from __future__ import annotations

from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CredentialsIn(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=1, max_length=72)

    @field_validator("username")
    @classmethod
    def strip_username(cls, value: str) -> str:
        stripped = value.strip()
        if not 2 <= len(stripped) <= 32:
            raise ValueError("用户名需为 2–32 个字符")
        return stripped


class RegisterResult(BaseModel):
    username: str


class PhoneIn(BaseModel):
    phone: str = Field(max_length=24)

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        phone = value.strip().replace(" ", "").replace("-", "").removeprefix("+86")
        if not re.fullmatch(r"1[3-9][0-9]{9}", phone):
            raise ValueError("请输入 11 位中国大陆手机号")
        return phone


class SmsRequestIn(PhoneIn):
    purpose: Literal["login", "register"]


class SmsProofIn(PhoneIn):
    challenge_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    code: str = Field(pattern=r"^[0-9]{6}$")


class VerifiedRegisterIn(SmsProofIn, CredentialsIn):
    pass


class PhoneBindingIn(SmsProofIn):
    password: str = Field(min_length=1, max_length=72)


class SmsChallengeOut(BaseModel):
    challenge_id: str
    expires_in: int
    resend_in: int
    demo_code: str | None = None


class AuthOptionsOut(BaseModel):
    sms_mode: Literal["disabled", "demo", "live"]
    requires_phone: bool


class MemberOut(BaseModel):
    customer_id: str
    username: str
    name: str
    phone: str | None = None
    verified_phone_hint: str | None = None
    avatar: str | None = None
    org_id: str | None = None
    org_ids: list[str] = Field(default_factory=list)


class LoginResult(MemberOut):
    session_id: str
    token: str
    expires_at: datetime
