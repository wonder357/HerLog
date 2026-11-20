from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _as_utc_iso(moment: datetime) -> str:
    return moment.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


class ChatCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=60)


class ChatRenameIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=60)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        stripped = " ".join(value.split())
        if not stripped:
            raise ValueError("标题不能为空")
        return stripped


class ChatMessageOut(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    source: str | None = None


class ChatSummaryOut(BaseModel):
    id: int
    title: str
    message_count: int
    updated_at: str


class ChatDetailOut(BaseModel):
    id: int
    title: str
    updated_at: str
    messages: list[ChatMessageOut]


def summary_out(chat_id: int, title: str, message_count: int, updated_at: datetime) -> ChatSummaryOut:
    return ChatSummaryOut(
        id=chat_id, title=title, message_count=message_count, updated_at=_as_utc_iso(updated_at)
    )


def detail_out(
    chat_id: int, title: str, updated_at: datetime, messages: list[ChatMessageOut]
) -> ChatDetailOut:
    return ChatDetailOut(
        id=chat_id, title=title, updated_at=_as_utc_iso(updated_at), messages=messages
    )
