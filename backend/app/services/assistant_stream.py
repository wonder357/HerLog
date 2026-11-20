from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

from app.core.config import settings
from app.core.errors import ApiError
from app.schemas.herlog import AssistantAnswerOut, AssistantRange, AssistantStreamIn
from app.services.deepseek_client import chat_stream

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是「她记」的女性健康记录助手，用简明中文回答一般的健康记录和日常护理问题。
你只能看到用户在本次对话输入的文字，无法读取或写入账号记录。需要查询记录时提示切换「查记录」。
答复用于一般信息交流。不要诊断、开药、给剂量、制定减重指令、给出受孕概率或具体排卵日。
资料不足时明确说明。涉及紧急或严重症状时，建议寻求当地线下医疗协助。
不要假扮医疗人员。只输出简洁正文，避免 Markdown 表格和链接。"""


def event(kind: str, **data: object) -> str:
    return "data: " + json.dumps({"type": kind, **data}, ensure_ascii=False) + "\n\n"


def completed(answer: AssistantAnswerOut) -> str:
    return event("complete", answer=answer.model_dump(mode="json"))


async def stream_assistant(
    payload: AssistantStreamIn, record_answer: AssistantAnswerOut | None,
) -> AsyncIterator[str]:
    if record_answer is not None:
        yield event("source", source="records")
        yield completed(record_answer)
        return

    if settings.assistant_model_mode == "fixture":
        yield event("source", source="fixture")
        example = ("可以从一项容易坚持的记录开始。", "例如记下日期和当时的感受，之后再按需要补充。")
        for part in example:
            yield event("delta", text=part)
        yield completed(AssistantAnswerOut(
            answer="".join(example),
            domain="general", range=AssistantRange(label="未指定范围"),
        ))
        return
    if not settings.HERLOG_MODEL_API_KEY.strip():
        yield event("error", message="首页助手尚未配置 DeepSeek API 密钥。")
        return

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for exchange in payload.history:
        messages.extend([
            {"role": "user", "content": exchange.question},
            {"role": "assistant", "content": exchange.answer},
        ])
    messages.append({"role": "user", "content": payload.question})
    parts: list[str] = []
    finished = False
    model_id = settings.HERLOG_MODEL_ID
    try:
        async with asyncio.timeout(settings.HERLOG_MODEL_TIMEOUT_SECONDS):
            async for chunk in chat_stream(messages, thinking=False, max_tokens=1000):
                if chunk.model_id:
                    model_id = chunk.model_id
                if chunk.text:
                    if not parts:
                        yield event("source", source="deepseek")
                    parts.append(chunk.text)
                    yield event("delta", text=chunk.text)
                if chunk.done:
                    finished = True
    except ApiError as failure:
        upstream = failure.data.get("status") if isinstance(failure.data, dict) else None
        logger.warning("assistant DeepSeek request failed: upstream=%s status=%s", upstream, failure.status_code)
        message = {
            401: "DeepSeek 密钥验证失败，请检查服务端配置。",
            402: "DeepSeek API 账户余额不足。",
            403: "DeepSeek 拒绝了当前服务端凭据。",
            429: "DeepSeek 请求较多，请稍后重试。",
        }.get(upstream, "暂时未能完成 DeepSeek 回答，请重试。")
        yield event("error", message=message)
        return
    except TimeoutError:
        yield event("error", message="DeepSeek 回答超时，请重试。")
        return

    answer = "".join(parts).strip()
    if not finished or not answer:
        yield event("error", message="回答中断，请重试。")
        return
    yield completed(AssistantAnswerOut(
        answer=answer, domain="general", range=AssistantRange(label="未指定范围"),
        model_id=model_id,
    ))
