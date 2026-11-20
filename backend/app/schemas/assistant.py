from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.herlog import AssistantAnswerOut, AssistantTopic


class HistoryPreferenceIn(BaseModel):
    enabled: bool = Field(strict=True)


class ConversationTitleIn(BaseModel):
    title: str = Field(max_length=48)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not 1 <= len(cleaned) <= 24 or any(ord(char) < 32 for char in cleaned):
            raise ValueError("请输入 1–24 个字符的单行标题")
        return cleaned


class ConversationOut(BaseModel):
    id: str
    title: str
    updated_at: str


class TurnOut(BaseModel):
    id: str
    question: str
    mode: Literal["general", "records"]
    topic: AssistantTopic | None = None
    status: Literal["pending", "complete", "failed", "stopped"]
    source: Literal["deepseek", "fixture", "records"] | None = None
    answer: AssistantAnswerOut | None = None
    partial: str | None = None
    error: str | None = None
