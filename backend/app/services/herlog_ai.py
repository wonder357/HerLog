"""她记的两处显式模型调用：观察已拍照片、解释程序算好的事实。

对应实施说明里的 `observe_skin(image, site)` 与 `answer_question(facts, question)`：
数字由服务端统计，模型只负责描述外观和用文字解释结论，不写入健康记录。
"""

from __future__ import annotations

import base64
from typing import Any

from app.core.config import settings
from app.core.errors import ApiError, invalid
from app.services.deepseek_client import chat, chat_json

SKIN_SITES = ("面部", "颈部", "手臂", "背部", "胸前", "腿部")
ALLOWED_MIME = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_BYTES = 3 * 1024 * 1024

SKIN_SYSTEM_PROMPT = """你是「她记」的皮肤外观观察助手，只描述照片里看得见的东西。

规则：
1. 只写外观：颜色、分布、边界、表面状态、数量级（如“少量”“零星”）。
2. 不给病名、严重程度评分、改善百分比，不推荐药物或治疗方案。
3. 看不清就写进 unclear，例如昏暗、模糊、角度不一致、有遮挡。
4. 照片看不出目标部位时，visible 可为空，并在 attention 说明没看到该部位。
5. 只输出 JSON 对象，三个键都是字符串数组，中文，每条不超过 40 字。"""

SKIN_JSON_HINT = """输出格式：
{"visible": ["..."], "unclear": ["..."], "attention": ["..."]}
visible 写看得见的外观，unclear 写看不清的原因，attention 写值得留意或需要补充拍照的地方。"""

QA_SYSTEM_PROMPT = """你是「她记」的记录问答助手，回答用户关于自己经期、体重、皮肤记录的问题。

规则：
1. 只用下面「事实」里的数字和日期，不补充、不推算、不编造任何新数字。
2. 事实为空时直接说明没有相关记录，并建议用首页快捷入口去记录。
3. 提到变化时写出取值口径与日期范围，例如“11-12 至 11-18，最后一次测量从 57.2 降到 56.8”。
4. 不做因果归因（例如不把长痘归因于经期），不给诊断、用药或减重指令；可以建议查看对应模块的记录。
5. 用户想录入（如“帮我记 56.8 kg”）时，说明对话只读，引导点「记体重」「记经期」「拍照分析」。
6. 中文，口语，三句话以内；不输出 JSON、不输出表格。"""


def _facts_text(facts: dict[str, Any]) -> str:
    """把程序算好的事实压成紧凑文本，避免把整表流水交给模型。"""

    lines: list[str] = []
    for key, value in facts.items():
        if value in (None, "", [], {}):
            continue
        lines.append(f"{key}: {value}")
    return "\n".join(lines) if lines else "（无记录）"


async def observe_skin(image: bytes, site: str, mime: str = "image/jpeg") -> dict[str, Any]:
    """单次皮肤观察。返回三段文字加模型标识，供结果页展示与保存。"""

    if site not in SKIN_SITES:
        raise invalid(f"部位只能是：{'、'.join(SKIN_SITES)}")
    if mime not in ALLOWED_MIME:
        raise invalid("仅支持 JPEG、PNG、GIF、WebP 图片")
    if not image:
        raise invalid("图片内容为空")
    if len(image) > MAX_IMAGE_BYTES:
        raise invalid("图片超过 3 MiB，请压缩或重拍")

    encoded = base64.b64encode(image).decode("ascii")
    messages = [
        {"role": "system", "content": SKIN_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"拍摄部位：{site}。\n{SKIN_JSON_HINT}"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{encoded}", "detail": "original"},
                },
            ],
        },
    ]
    data = await chat_json(
        messages,
        required=("visible", "unclear", "attention"),
        thinking=False,
        temperature=0.2,
        max_tokens=800,
    )
    return {
        "site": site,
        "visible": _as_list(data.get("visible")),
        "unclear": _as_list(data.get("unclear")),
        "attention": _as_list(data.get("attention")),
        "model_id": settings.HERLOG_MODEL_ID,
        "prompt_version": settings.HERLOG_PROMPT_VERSION,
    }


async def answer_question(facts: dict[str, Any], question: str) -> str:
    """首页只读问答。facts 由路由层按当前会员统计后传入。"""

    question = question.strip()
    if not question:
        raise invalid("问题不能为空")
    if len(question) > 500:
        raise invalid("问题过长，请控制在 500 字以内")

    messages = [
        {"role": "system", "content": QA_SYSTEM_PROMPT},
        {"role": "user", "content": f"事实：\n{_facts_text(facts)}\n\n用户问题：{question}"},
    ]
    result = await chat(
        messages,
        thinking=False,
        temperature=0.3,
        max_tokens=500,
    )
    if not result.content.strip():
        raise ApiError(502, "模型没有返回内容，请重试")
    return result.content.strip()


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value)]
