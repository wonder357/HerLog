from __future__ import annotations

from datetime import datetime

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


class MemberOut(BaseModel):
    customer_id: str
    username: str
    name: str
    phone: str | None = None
    avatar: str | None = None
    org_id: str | None = None
    org_ids: list[str] = Field(default_factory=list)


class LoginResult(MemberOut):
    session_id: str
    token: str
    expires_at: datetime
