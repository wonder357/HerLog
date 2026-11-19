"""图片入参校验：字节上限、格式、可解码性和像素上限都在解码前/时检查。"""

from __future__ import annotations

import base64
import binascii
import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.errors import invalid

FORMAT_TO_MIME = {"JPEG": "image/jpeg", "PNG": "image/png"}


@dataclass(frozen=True)
class DecodedImage:
    data: bytes
    mime: str
    width: int
    height: int
    brightness: float
    contrast: float

    @property
    def quality(self) -> tuple[str, str]:
        if self.width < 480 or self.height < 480:
            return "limited", "图片偏小，看不清细节；建议靠得更近再拍一张。"
        if self.brightness < 45 or self.brightness > 235:
            return "limited", "光线偏暗或过曝，部分区域看不清；建议在自然光下重拍。"
        if self.contrast < 18:
            return "limited", "画面有点模糊或角度不一致，细节看不清；可以重拍一次。"
        return "good", "画面清晰，光线足够。"


def decode_image(image_base64: str, declared_mime: str) -> DecodedImage:
    try:
        raw = base64.b64decode(image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise invalid("图片数据无法解析，请重新选择图片") from exc
    if not raw:
        raise invalid("图片为空，请重新选择")
    if len(raw) > settings.SKIN_MAX_UPLOAD_BYTES:
        raise invalid("图片超过 3 MiB，请压缩后再试")
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            fmt = probe.format
            width, height = probe.size
            pixels = width * height
            if fmt not in FORMAT_TO_MIME:
                raise invalid("只支持 JPEG 或 PNG 图片")
            if pixels <= 0 or pixels > settings.SKIN_MAX_PIXELS:
                raise invalid("图片像素过大，请缩小后再试")
            probe.load()
            gray = probe.convert("L").resize((64, 64))
            values = list(gray.tobytes())
    except UnidentifiedImageError as exc:
        raise invalid("图片无法解码，请重新选择") from exc
    except OSError as exc:
        raise invalid("图片无法解码，请重新选择") from exc
    mime = FORMAT_TO_MIME[fmt]
    if mime != declared_mime:
        raise invalid(f"图片格式与声明不一致（实际为 {mime}）")
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return DecodedImage(
        data=raw,
        mime=mime,
        width=width,
        height=height,
        brightness=mean,
        contrast=variance**0.5,
    )
