from typing import Literal

from pydantic import Field, field_validator

from app.schemas.wellness import StrictInput

Category = Literal["experience", "question", "checkin", "cycle", "training"]
DiscussionView = Literal["all", "saved", "mine"]
DiscussionSort = Literal["latest", "popular"]
ReactionKind = Literal["like", "save"]


class DiscussionBody(StrictInput):
    body: str = Field(min_length=1, max_length=600)

    @field_validator("body", mode="before")
    @classmethod
    def trim_body(cls, value):
        return value.strip() if isinstance(value, str) else value


class DiscussionEditIn(DiscussionBody):
    title: str = Field(min_length=2, max_length=60)
    category: Category

    @field_validator("title", mode="before")
    @classmethod
    def trim_title(cls, value):
        return value.strip() if isinstance(value, str) else value


class DiscussionPostIn(DiscussionEditIn):
    client_key: str = Field(min_length=8, max_length=36)
    checkin_id: int | None = Field(default=None, gt=0, strict=True)


class DiscussionReplyIn(DiscussionBody):
    body: str = Field(min_length=1, max_length=300)
    client_key: str = Field(min_length=8, max_length=36)
