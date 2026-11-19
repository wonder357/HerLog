"""DeepSeek Chat Completions 适配：非流式、流式与结构化输出。

DeepSeek 兼容 OpenAI 协议，端点固定为 `{base_url}/chat/completions`。
思考模式由 `thinking` 开关和 `reasoning_effort` 强度控制，思维链在 `reasoning_content` 返回；
思考模式下 `temperature` 等采样参数不生效，所以这里只在非思考模式下发采样参数。

模型调用失败统一转成 `ApiError`，路由层无需关心 httpx 细节；手动记录功能不依赖本模块。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

from app.core.config import settings
from app.core.errors import ApiError

DEFAULT_BASE_URL = "https://api.deepseek.com"
Effort = Literal["low", "high", "max"]


@dataclass(slots=True)
class ChatResult:
    """一次非流式调用的结果。"""

    content: str
    reasoning: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StreamChunk:
    """流式增量：本段正文、本段思维链、或末尾的用量统计。"""

    text: str = ""
    reasoning: str = ""
    usage: dict[str, Any] | None = None
    done: bool = False


def endpoint() -> str:
    base = (settings.HERLOG_MODEL_BASE_URL or DEFAULT_BASE_URL).rstrip("/")
    return base if base.endswith("/chat/completions") else f"{base}/chat/completions"


def headers() -> dict[str, str]:
    key = settings.HERLOG_MODEL_API_KEY.strip()
    if not key:
        raise ApiError(500, "未配置 HERLOG_MODEL_API_KEY，无法调用模型")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def build_payload(
    messages: Sequence[dict[str, Any]],
    *,
    model: str | None = None,
    thinking: bool = True,
    reasoning_effort: Effort = "high",
    temperature: float | None = None,
    max_tokens: int | None = None,
    json_object: bool = False,
    stream: bool = False,
    tools: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """拼装请求体。纯函数，方便单独断言字段。"""

    payload: dict[str, Any] = {
        "model": model or settings.HERLOG_MODEL_ID,
        "messages": list(messages),
        "stream": stream,
        "thinking": {"type": "enabled" if thinking else "disabled"},
    }
    if thinking:
        payload["reasoning_effort"] = reasoning_effort
    elif temperature is not None:
        payload["temperature"] = temperature
    if max_tokens:
        payload["max_tokens"] = max_tokens
    if json_object:
        payload["response_format"] = {"type": "json_object"}
    if tools:
        payload["tools"] = list(tools)
    return payload


async def chat(
    messages: Sequence[dict[str, Any]],
    *,
    model: str | None = None,
    thinking: bool = True,
    reasoning_effort: Effort = "high",
    temperature: float | None = None,
    max_tokens: int | None = None,
    json_object: bool = False,
    tools: Sequence[dict[str, Any]] | None = None,
) -> ChatResult:
    """非流式对话。首页问答走这里：一次请求拿到完整回答。"""

    payload = build_payload(
        messages,
        model=model,
        thinking=thinking,
        reasoning_effort=reasoning_effort,
        temperature=temperature,
        max_tokens=max_tokens,
        json_object=json_object,
        tools=tools,
    )
    data = await _post(payload)
    choices = data.get("choices") or [{}]
    message = choices[0].get("message") or {}
    return ChatResult(
        content=message.get("content") or "",
        reasoning=message.get("reasoning_content") or "",
        model=data.get("model") or payload["model"],
        usage=data.get("usage") or {},
    )


async def chat_json(
    messages: Sequence[dict[str, Any]],
    *,
    required: Sequence[str] = (),
    **kwargs: Any,
) -> dict[str, Any]:
    """要求模型只输出 JSON 对象，并校验必需字段。皮肤观察走这里。"""

    result = await chat(messages, json_object=True, **kwargs)
    try:
        data = json.loads(result.content)
    except json.JSONDecodeError as exc:
        raise ApiError(502, "模型返回内容不是合法 JSON，请重试") from exc
    if not isinstance(data, dict):
        raise ApiError(502, "模型返回的 JSON 顶层不是对象")
    missing = [key for key in required if key not in data]
    if missing:
        raise ApiError(502, f"模型返回缺少字段：{'、'.join(missing)}")
    return data


async def chat_stream(
    messages: Sequence[dict[str, Any]],
    *,
    model: str | None = None,
    thinking: bool = True,
    reasoning_effort: Effort = "high",
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> AsyncIterator[StreamChunk]:
    """流式对话。逐段 yield，最后一段 `done=True`；断连时直接抛出 `ApiError`。"""

    payload = build_payload(
        messages,
        model=model,
        thinking=thinking,
        reasoning_effort=reasoning_effort,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    try:
        async with httpx.AsyncClient(timeout=settings.HERLOG_MODEL_TIMEOUT_SECONDS) as client:
            async with client.stream("POST", endpoint(), headers=headers(), json=payload) as response:
                if response.status_code != 200:
                    body = (await response.aread()).decode("utf-8", "replace")
                    raise _model_error(response.status_code, body)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        yield StreamChunk(done=True)
                        return
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choice = (event.get("choices") or [{}])[0]
                    delta = choice.get("delta") or {}
                    chunk = StreamChunk(
                        text=delta.get("content") or "",
                        reasoning=delta.get("reasoning_content") or "",
                        usage=event.get("usage"),
                    )
                    if chunk.text or chunk.reasoning or chunk.usage:
                        yield chunk
    except httpx.TimeoutException as exc:
        raise ApiError(504, "模型响应超时，请重试") from exc
    except httpx.HTTPError as exc:
        raise ApiError(503, "模型服务连接失败，请重试") from exc


async def _post(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=settings.HERLOG_MODEL_TIMEOUT_SECONDS) as client:
            response = await client.post(endpoint(), headers=headers(), json=payload)
    except httpx.TimeoutException as exc:
        raise ApiError(504, "模型响应超时，请重试") from exc
    except httpx.HTTPError as exc:
        raise ApiError(503, "模型服务连接失败，请重试") from exc
    if response.status_code != 200:
        raise _model_error(response.status_code, response.text)
    return response.json()


def _model_error(status: int, body: str) -> ApiError:
    """把上游状态码翻成前端可展示的文案，原始细节留在 data 里便于排查。"""

    detail = body[:500]
    if status in (401, 403):
        return ApiError(500, "模型服务鉴权失败，请检查 HERLOG_MODEL_API_KEY", {"detail": detail})
    if status == 429:
        return ApiError(503, "模型服务繁忙，请稍后重试", {"detail": detail})
    if status >= 500:
        return ApiError(503, "模型服务暂时不可用，请稍后重试", {"detail": detail})
    return ApiError(502, "模型请求被拒绝，请重试", {"status": status, "detail": detail})
