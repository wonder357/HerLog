"""体重 tag 的两处模型调用：饮食热量估算、教练周报与对话。

约定与皮肤观察一致：数字由服务端算，模型只做识别与解释。
`fixture` 模式不联网，用规则估算和调用方给的固定文案，并带演示标记；
`live` 模式走 DeepSeek 的 chat/completions，输出校验通过才展示。
"""

from __future__ import annotations

import json
from typing import Any

from app.core.config import settings
from app.core.errors import ApiError
from app.logic import nutrition
from app.schemas.weight_plus import EstimateItemOut, MealEstimateOut
from app.services import knowledge
from app.services.deepseek_client import chat_sync

MEAL_SYSTEM_PROMPT = """你是「她记」的饮食热量估算助手。用户用一句话描述吃了什么，你估算热量和三大营养素。

规则：
1. 按中国常见的一份份量估算，items 里每项写清 name（食物名）、portion（份量，如「一碗约 150g」）、kcal、protein_g、carb_g、fat_g。
2. 最多 6 项；看不出份量时按常见一份估，不要追问。
3. 没有具体食物（如「吃撑了」「随便吃了点」）时 items 返回空数组。
4. 不给健康评价、不劝节食、不推荐产品。
5. 只输出 JSON：{"items": [...], "note": "不超过 40 字的估算说明"}"""

REPORT_SYSTEM_PROMPT = """你是「她记」的体重教练，根据服务端算好的事实写一段周报。

规则：
1. 只用事实里的数字和日期，不补充、不推算新的数字，不做因果归因。
2. 不给诊断、不用药建议、不推荐代餐或极端节食；数字异常时建议就医或线下咨询。
3. summary 三句以内，语气平实；highlights 写 1~3 条做得好的地方；cautions 写 0~3 条要注意的地方。
4. 中文，不用表情和表格。
5. 只输出 JSON：{"summary": str, "highlights": [str], "cautions": [str]}"""

CHAT_SYSTEM_PROMPT = """你是「她记」体重模块的只读教练，回答用户关于自己体重、饮食、运动记录的问题。

规则：
1. 只用「事实」和「参考知识」里的内容，不编造数字，不引用没给出的资料。
2. 不给疾病诊断、不给药物或手术建议、不鼓吹断食或极端热量缺口。
3. 用户想录入（例如「帮我记 56.8」）时，说明对话只读，引导使用「记体重」「记饮食」入口。
4. 提到变化时写出日期范围和取值口径。
5. 中文口语，三句话以内，不输出 JSON。"""


def _parse_json(result_content: str) -> dict[str, Any]:
    try:
        data = json.loads(result_content)
    except json.JSONDecodeError as exc:
        raise ApiError(502, "模型返回内容不是合法 JSON，请重试") from exc
    if not isinstance(data, dict):
        raise ApiError(502, "模型返回的 JSON 顶层不是对象")
    return data


def _number(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, int(round(value)))


def estimate_meal(text: str, meal_type: str) -> MealEstimateOut:
    """先规则估算，live 模式再让模型细化；总额一律由服务端重算。"""

    rule = nutrition.estimate_by_text(text)
    if settings.HERLOG_MODEL_MODE != "live":
        return MealEstimateOut(
            items=[
                EstimateItemOut(
                    name=item.name,
                    portion=item.portion,
                    kcal=item.kcal,
                    protein_g=item.protein_g,
                    carb_g=item.carb_g,
                    fat_g=item.fat_g,
                )
                for item in rule.items
            ],
            kcal=rule.kcal,
            protein_g=rule.protein_g,
            carb_g=rule.carb_g,
            fat_g=rule.fat_g,
            confidence=rule.confidence,
            note=f"（演示估算）{rule.note}",
            demo_sample=True,
        )

    result = chat_sync(
        [
            {"role": "system", "content": MEAL_SYSTEM_PROMPT},
            {"role": "user", "content": f"餐次：{meal_type}\n描述：{text}"},
        ],
        thinking=False,
        temperature=0.2,
        max_tokens=700,
        json_object=True,
    )
    data = _parse_json(result.content)
    raw_items = data.get("items")
    items: list[EstimateItemOut] = []
    if isinstance(raw_items, list):
        for entry in raw_items[:6]:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name") or "").strip()
            if not name:
                continue
            items.append(
                EstimateItemOut(
                    name=name[:20],
                    portion=str(entry.get("portion") or "一份")[:24],
                    kcal=_number(entry.get("kcal")),
                    protein_g=_number(entry.get("protein_g")),
                    carb_g=_number(entry.get("carb_g")),
                    fat_g=_number(entry.get("fat_g")),
                )
            )
    note = str(data.get("note") or "").strip()[:80] or "按模型估算，实际以食物称重和做法为准。"
    return MealEstimateOut(
        items=items,
        kcal=sum(item.kcal for item in items),
        protein_g=sum(item.protein_g for item in items),
        carb_g=sum(item.carb_g for item in items),
        fat_g=sum(item.fat_g for item in items),
        confidence="high" if items else "none",
        note=note,
        demo_sample=False,
    )


def coach_report(facts: list[str], fallback: tuple[str, list[str], list[str]]) -> tuple[str, list[str], list[str], str, bool]:
    """返回（小结、亮点、提醒、模型标识、是否演示）。"""

    if settings.HERLOG_MODEL_MODE != "live":
        summary, highlights, cautions = fallback
        return summary, highlights, cautions, f"fixture:{settings.HERLOG_MODEL_ID}", True

    result = chat_sync(
        [
            {"role": "system", "content": REPORT_SYSTEM_PROMPT},
            {"role": "user", "content": "事实：\n" + "\n".join(facts)},
        ],
        thinking=False,
        temperature=0.3,
        max_tokens=700,
        json_object=True,
    )
    data = _parse_json(result.content)
    summary = str(data.get("summary") or "").strip()
    if not summary:
        raise ApiError(502, "模型没有返回周报内容，请重试")
    return (
        summary,
        [str(item).strip() for item in data.get("highlights") or [] if str(item).strip()][:3],
        [str(item).strip() for item in data.get("cautions") or [] if str(item).strip()][:3],
        result.model,
        False,
    )


def coach_chat(
    facts: list[str], question: str, fallback_answer: str
) -> tuple[str, list[knowledge.Topic], str, bool]:
    """返回（回答、引用的知识条目、模型标识、是否演示）。"""

    hits = knowledge.search(question)
    if settings.HERLOG_MODEL_MODE != "live":
        return fallback_answer, hits, f"fixture:{settings.HERLOG_MODEL_ID}", True

    knowledge_text = "\n".join(
        f"{topic.title}：{topic.summary}（来源：{topic.source}）" for topic in hits
    ) or "（无）"
    result = chat_sync(
        [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"事实：\n" + "\n".join(facts) + f"\n\n参考知识：\n{knowledge_text}"
                    f"\n\n用户问题：{question}"
                ),
            },
        ],
        thinking=False,
        temperature=0.3,
        max_tokens=500,
    )
    answer = result.content.strip()
    if not answer:
        raise ApiError(502, "模型没有返回内容，请重试")
    return answer, hits, result.model, False
