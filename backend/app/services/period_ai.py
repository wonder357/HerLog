"""经期模块的模型调用：把服务端算好的周期事实交给模型，产出一段小结与三条建议。

约定与体重、皮肤一致：事实与日期都由服务端算，模型只做解释，不产出新数字。
`fixture` 模式不联网，用规则文案并带演示标记；`live` 模式走 DeepSeek 的
chat/completions（与首页问答同一套客户端）；模型不可用时降级为规则文案，
页面仍有内容可看，同时用 `degraded` 标记出来。
"""

from __future__ import annotations

import json

from app.core.config import settings
from app.core.errors import ApiError
from app.services.deepseek_client import chat_sync

INSIGHT_SYSTEM_PROMPT = """你是「她记」的经期记录助手，根据服务端给出的周期事实写一段小结和日常建议。

规则：
1. 只用事实里的日期、天数与阶段，不推算新数字，不预测受孕概率，不判断是否怀孕。
2. 不做疾病诊断，不给药物、剂量、补剂用量，不推荐品牌或产品。
3. 排卵日与易孕期只能表述为估算，明确说明不能用于避孕，也不能作为备孕依据。
4. 建议要日常、可执行、温和：饮食按普通均衡饮食，运动按强度与时长，健康作息按睡眠与观察记录。
5. 出现明显异常（如经量骤增、持续剧痛、推迟超过一周）时，建议线下就医，不自行处理。
6. 中文，不用表情和表格，不要写项目符号前缀，每条不超过 40 字。

只输出 JSON：{"summary": str, "diet": [str], "exercise": [str], "wellbeing": [str], "cautions": [str]}
summary 两句以内；diet/exercise/wellbeing 各 2~3 条；cautions 0~2 条。"""

GROUP_TITLES = (
    ("diet", "饮食"),
    ("exercise", "运动"),
    ("wellbeing", "作息与健康"),
)


def _clean(items: object, limit: int = 3) -> list[str]:
    if not isinstance(items, list):
        return []
    cleaned: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if text:
            cleaned.append(text[:60])
        if len(cleaned) >= limit:
            break
    return cleaned


def _parse(content: str) -> dict:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ApiError(502, "模型返回内容不是合法 JSON，请重试") from exc
    if not isinstance(data, dict):
        raise ApiError(502, "模型返回的 JSON 顶层不是对象")
    return data


def build_insight(
    facts: list[str],
    fallback: tuple[str, dict[str, list[str]], list[str]],
) -> tuple[str, dict[str, list[str]], list[str], str, bool, bool]:
    """返回（小结、分组建议、注意事项、模型标识、是否演示、是否降级）。"""

    summary, groups, cautions = fallback
    if settings.HERLOG_MODEL_MODE != "live":
        return summary, groups, cautions, f"fixture:{settings.HERLOG_MODEL_ID}", True, False

    try:
        result = chat_sync(
            [
                {"role": "system", "content": INSIGHT_SYSTEM_PROMPT},
                {"role": "user", "content": "事实：\n" + "\n".join(facts)},
            ],
            thinking=False,
            temperature=0.4,
            max_tokens=700,
            json_object=True,
        )
        data = _parse(result.content)
    except ApiError:
        # 模型不可用时保留可用的规则建议，标记为降级，前端仍可展示与重试。
        return summary, groups, cautions, "fixture:fallback", True, True

    text = str(data.get("summary") or "").strip()
    if not text:
        return summary, groups, cautions, "fixture:fallback", True, True

    live_groups = {key: _clean(data.get(key)) for key, _ in GROUP_TITLES}
    merged = {
        key: live_groups.get(key) or groups.get(key, [])
        for key, _ in GROUP_TITLES
    }
    live_cautions = _clean(data.get("cautions"), limit=2)
    return text[:400], merged, live_cautions or cautions, result.model, False, False
