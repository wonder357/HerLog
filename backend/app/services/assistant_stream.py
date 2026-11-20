from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable

from app.core.config import settings
from app.core.errors import ApiError
from app.schemas.herlog import AssistantAnswerOut, AssistantRange, AssistantStreamIn
from app.services.deepseek_client import chat_stream

logger = logging.getLogger("herlog")

# (回答正文, 来源) -> 对话 id；由路由层提供，负责把一问一答写库。
SaveExchange = Callable[[str, str], int]

SYSTEM_PROMPT = """你是「她记」的女性健康记录助手，用简明中文回答一般的健康记录和日常护理问题。
你只能看到用户在本次对话输入的文字，无法读取或写入账号记录。需要查询记录时提示切换「查记录」。
答复用于一般信息交流。不要诊断、开药、给剂量、制定减重指令、给出受孕概率或具体排卵日。
资料不足时明确说明。涉及紧急或严重症状时，建议寻求当地线下医疗协助。
不要假扮医疗人员。只输出简洁正文，避免 Markdown 表格和链接。"""


def event(kind: str, **data: object) -> str:
    return "data: " + json.dumps({"type": kind, **data}, ensure_ascii=False) + "\n\n"


def completed(answer: AssistantAnswerOut, chat_id: int | None = None) -> str:
    return event("complete", answer=answer.model_dump(mode="json"), chat_id=chat_id)


def _save(save: SaveExchange | None, answer: str, source: str) -> int | None:
    """写库失败不影响已经流出的正文，只记录日志。"""

    if save is None:
        return None
    try:
        return save(answer, source)
    except Exception as exc:  # pragma: no cover - 依赖外部数据库
        logger.warning("assistant chat save failed: %s", exc)
        return None


async def stream_assistant(
    payload: AssistantStreamIn,
    record_answer: AssistantAnswerOut | None,
    save: SaveExchange | None = None,
) -> AsyncIterator[str]:
    """流式回答。`save` 在回答定稿后写入一问一答，返回对话 id 供前端续聊。"""

    if record_answer is not None:
        yield event("source", source="records")
        yield completed(record_answer, _save(save, record_answer.answer, "records"))
        return

    live = settings.assistant_model_mode == "live"
    yield event("source", source="deepseek" if live else "fixture")
    if not live:
        example = ("可以从一项容易坚持的记录开始。", "例如记下日期和当时的感受，之后再按需要补充。")
        for part in example:
            yield event("delta", text=part)
        answer = AssistantAnswerOut(
            answer="".join(example),
            domain="general",
            range=AssistantRange(label="未指定范围"),
        )
        yield completed(answer, _save(save, answer.answer, "fixture"))
        return

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for exchange in payload.history:
        messages.extend(
            [
                {"role": "user", "content": exchange.question},
                {"role": "assistant", "content": exchange.answer},
            ]
        )
    messages.append({"role": "user", "content": payload.question})
    parts: list[str] = []
    finished = False
    try:
        async with asyncio.timeout(settings.HERLOG_MODEL_TIMEOUT_SECONDS):
            async for chunk in chat_stream(messages, thinking=False, max_tokens=1000):
                if chunk.text:
                    parts.append(chunk.text)
                    yield event("delta", text=chunk.text)
                if chunk.done:
                    finished = True
    except (ApiError, TimeoutError):
        yield event("error", message="暂时未能完成回答，请重试。")
        return

    answer = "".join(parts).strip()
    if not finished or not answer:
        yield event("error", message="回答中断，请重试。")
        return
    result = AssistantAnswerOut(
        answer=answer,
        domain="general",
        range=AssistantRange(label="未指定范围"),
        model_id=settings.HERLOG_MODEL_ID,
    )
    yield completed(result, _save(save, answer, "deepseek"))
