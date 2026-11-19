from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings


class PrivatePhotoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mime: Literal["image/jpeg", "image/png"]
    image_base64: str = Field(min_length=32, max_length=4 * ((settings.SKIN_MAX_UPLOAD_BYTES + 2) // 3))


class PrivatePhotoChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    photo: PrivatePhotoIn | None
