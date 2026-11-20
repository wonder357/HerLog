from typing import Literal

from pydantic import Field, field_validator

from app.schemas.private_photo import PrivatePhotoIn
from app.schemas.wellness import StrictInput

Category = Literal["experience", "question", "checkin"]
# 公开：展示昵称；匿名：只显示「匿名成员」。作者自己始终能看到自己的帖子。
Visibility = Literal["public", "anonymous"]
Sort = Literal["latest", "popular"]
Scope = Literal["all", "mine"]

MAX_POST_IMAGES = 3


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
    visibility: Visibility = "anonymous"
    checkin_id: int | None = Field(default=None, gt=0, strict=True)
    images: list[PrivatePhotoIn] = Field(default_factory=list, max_length=MAX_POST_IMAGES)

    @field_validator("title", mode="before")
    @classmethod
    def trim_title(cls, value):
        return value.strip() if isinstance(value, str) else value


class DiscussionReplyIn(DiscussionText):
    body: str = Field(min_length=1, max_length=300)
    visibility: Visibility = "anonymous"
