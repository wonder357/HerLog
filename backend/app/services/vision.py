"""图文模型适配。

对外只有两个明确调用：
- `observe_skin(image, site)` 单次可见外观描述；
- `answer_question(facts, question)` 只解释程序算出的数字。

`fixture` 模式用于现场断网恢复，结果必须带「演示样例」标记；
`live` 模式调用 OpenAI 兼容的 chat/completions 端点，输出校验通过才展示。
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.errors import ApiError
from app.services.image_validation import DecodedImage

PROMPT_VERSION = "herlog-skin-v1"

SYSTEM_PROMPT = (
    "你是一名皮肤观察助手，只根据照片描述可见外观。"
    "禁止给出病名、严重程度评分、改善百分比或治疗建议，也不做因果归因。"
    "必须只输出 JSON：{\"visible\": str, \"unclear\": str, \"attention\": str, \"quality\": \"good\"|\"limited\"}。"
    "三段文字各自不超过 120 字，语气中性。"
)


@dataclass(frozen=True)
class SkinObservationResult:
    visible: str
    unclear: str
    attention: str
    quality: str
    quality_message: str
    model_id: str
    prompt_version: str
    demo_sample: bool


def _unavailable(reason: str) -> ApiError:
    return ApiError(503, f"模型服务暂时不可用（{reason}），已保留所选图片，请重试")


def observe_skin(image: DecodedImage, site: str) -> SkinObservationResult:
    quality, quality_message = image.quality
    if settings.HERLOG_MODEL_MODE == "live":
        text = _live_observe(image, site)
        return SkinObservationResult(
            visible=text["visible"],
            unclear=text["unclear"],
            attention=text["attention"],
            quality=quality,
            quality_message=quality_message,
            model_id=settings.HERLOG_MODEL_ID,
            prompt_version=PROMPT_VERSION,
            demo_sample=False,
        )
    return SkinObservationResult(
        visible=f"（演示样例）{site}照片中可见皮肤表面纹理较均匀，未见明显突起或破损描述依据。",
        unclear=f"（演示样例）光线和角度有限，{site}边缘区域的细节看不清。",
        attention="（演示样例）若有持续不适或明显变化，建议线下咨询医生；本观察不构成诊断。",
        quality=quality,
        quality_message=quality_message,
        model_id=f"fixture:{settings.HERLOG_MODEL_ID}",
        prompt_version=PROMPT_VERSION,
        demo_sample=True,
    )


def answer_question(facts: str, question: str) -> str | None:
    """live 模式让模型解释给定事实；fixture 模式返回 None，由服务端用固定文案回答。"""

    if settings.HERLOG_MODEL_MODE != "live":
        return None
    if not settings.HERLOG_MODEL_BASE_URL:
        raise _unavailable("未配置推理服务地址")
    payload = {
        "model": settings.HERLOG_MODEL_ID,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你只是把给定的记录事实用中文解释清楚。不得编造事实里没有的数据，"
                    "不得给出诊断、因果结论或减重指令，不得写入任何记录。"
                ),
            },
            {"role": "user", "content": f"已保存的事实：\n{facts}\n\n用户的问题：{question}"},
        ],
    }
    data = _post_chat(payload)
    reply = data.get("answer") if isinstance(data, dict) else None
    if isinstance(reply, str) and reply.strip():
        return reply.strip()
    raise _unavailable("返回格式不符合约定")


def _live_observe(image: DecodedImage, site: str) -> dict:
    if not settings.HERLOG_MODEL_BASE_URL:
        raise _unavailable("未配置推理服务地址")
    encoded = base64.b64encode(image.data).decode("ascii")
    payload = {
        "model": settings.HERLOG_MODEL_ID,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"部位：{site}。请描述这张照片的可见外观。"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{image.mime};base64,{encoded}"},
                    },
                ],
            },
        ],
    }
    data = _post_chat(payload)
    parsed = data.get("skin") if isinstance(data, dict) else None
    if not isinstance(parsed, dict):
        raise _unavailable("返回格式不符合约定")
    cleaned: dict[str, str] = {}
    for key in ("visible", "unclear", "attention"):
        value = parsed.get(key)
        if not isinstance(value, str) or not value.strip():
            raise _unavailable("返回缺少字段")
        cleaned[key] = value.strip()[:500]
    quality = parsed.get("quality")
    cleaned["quality"] = quality if quality in ("good", "limited") else "limited"
    return cleaned


def _post_chat(payload: dict) -> dict:
    base = settings.HERLOG_MODEL_BASE_URL.rstrip("/")
    url = f"{base}/chat/completions" if base.endswith("/v1") else f"{base}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.HERLOG_MODEL_API_KEY:
        headers["Authorization"] = f"Bearer {settings.HERLOG_MODEL_API_KEY}"
    payload = {**payload, "response_format": {"type": "json_object"}}
    try:
        response = httpx.post(
            url, json=payload, headers=headers, timeout=settings.HERLOG_MODEL_TIMEOUT_SECONDS
        )
    except httpx.HTTPError as exc:
        raise _unavailable(type(exc).__name__) from exc
    if response.status_code >= 400:
        raise _unavailable(f"HTTP {response.status_code}")
    try:
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise _unavailable("返回不是合法 JSON") from exc
