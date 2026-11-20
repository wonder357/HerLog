from typing import Literal

from pydantic import Field, field_validator

from app.schemas.wellness import StrictInput

Category = Literal["experience", "question", "checkin"]


class DiscussionText(StrictInput):
    body: str = Field(min_length=1, max_length=600)
    client_key: str = Field(min_length=8, max_length=36)

    @field_validator("body", mode="before")
    @classmethod
    def trim_body(cls, value):
        return value.strip() if isinstance(value, str) else value


class DiscussionPostIn(DiscussionText):
    title: str = Field(min_length=2, max_length=60)
    category: Category
    checkin_id: int | None = Field(default=None, gt=0, strict=True)

    @field_validator("title", mode="before")
    @classmethod
    def trim_title(cls, value):
        return value.strip() if isinstance(value, str) else value


class DiscussionReplyIn(DiscussionText):
    body: str = Field(min_length=1, max_length=300)
