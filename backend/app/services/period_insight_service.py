"""经期页的周期小结：服务端先算事实，再交给 `period_ai` 生成建议。

事实口径与月历、周期阶段完全一致：都来自 `period_service.list_periods` 与
`cycle_context.current_phase`，所以排卵日、易孕期不会出现两套算法。
`fixture` 模式用规则文案；`live` 模式走 DeepSeek，失败时降级为规则文案。
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import local_today
from app.models.herlog import Feeling
from app.schemas.herlog import CycleInsightOut, InsightGroupOut
from app.services import cycle_context, period_ai, period_service

CACHE_TTL_SECONDS = 6 * 3600
FEELING_WINDOW_DAYS = 30

PHASE_LABELS = {
    "menstrual": "月经期",
    "follicular": "卵泡期",
    "ovulatory": "易孕期",
    "luteal": "黄体期",
    "unknown": "阶段待记录",
}

_CACHE: dict[str, tuple[float, CycleInsightOut]] = {}


def clear_cache() -> None:
    _CACHE.clear()


def _feeling_facts(session: Session, customer_id: str, today: date) -> tuple[list[str], str]:
    """最近 30 天的感受记录，只统计已有字段，不推断因果。"""

    start = today - timedelta(days=FEELING_WINDOW_DAYS - 1)
    rows = list(session.scalars(
        select(Feeling).where(
            Feeling.customer_id == customer_id,
            Feeling.day >= start,
            Feeling.day <= today,
        )
    ))
    if not rows:
        return ["最近 30 天没有感受记录"], ""
    symptoms: dict[str, int] = {}
    moods: dict[str, int] = {}
    for row in rows:
        for tag in row.symptoms or []:
            symptoms[tag] = symptoms.get(tag, 0) + 1
        if row.mood:
            moods[row.mood] = moods.get(row.mood, 0) + 1

    def top(counter: dict[str, int]) -> str:
        ordered = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        return "、".join(f"{name} {count} 天" for name, count in ordered[:3])

    facts = [f"最近 {FEELING_WINDOW_DAYS} 天记录感受 {len(rows)} 天"]
    summary_bits: list[str] = []
    if symptoms:
        facts.append("身体感受：" + top(symptoms))
        summary_bits.append(top(symptoms))
    if moods:
        facts.append("心情：" + top(moods))
        summary_bits.append("心情" + top(moods))
    return facts, "；".join(summary_bits)


def _iso(value: object) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _normalize(raw: dict) -> dict:
    """把服务层的 date 对象统一成 ISO 字符串，事实文本与签名都按字符串处理。"""

    prediction = dict(raw["prediction"])
    for key in ("predicted_range", "fertile_window"):
        window = prediction.get(key)
        if isinstance(window, dict):
            prediction[key] = {name: _iso(day) for name, day in window.items()}
    prediction["ovulation_day"] = _iso(prediction.get("ovulation_day"))
    prediction["expected_start"] = _iso(prediction.get("expected_start"))
    return {
        "items": [item.model_dump(mode="json") for item in raw["items"]],
        "prediction": prediction,
        "status": raw["status"],
    }


def _facts(
    data: dict, phase: str, basis: str, feeling_facts: list[str], today: date
) -> list[str]:
    prediction = data["prediction"]
    status = data["status"]
    facts = [f"今天：{today.isoformat()}", f"当前阶段：{PHASE_LABELS[phase]}（{'已记录' if basis == 'recorded' else '估算'}）"]
    items = data["items"]
    if items:
        latest = items[0]
        end = latest["end_day"] or "未记录结束"
        facts.append(
            f"最近一次经期：{latest['start_day']} 至 {end}"
            + (f"，持续 {latest['duration_days']} 天" if latest["duration_days"] else "")
        )
    if status.get("in_period"):
        facts.append(f"今天是经期第 {status['day_index']} 天")
    if prediction.get("estimate_days"):
        facts.append(f"估算周期长度：{prediction['estimate_days']} 天（最近 {prediction.get('cycle_count')} 个间隔）")
    if prediction.get("duration_days"):
        facts.append(f"估算经期长度：{prediction['duration_days']} 天")
    if prediction.get("predicted_range"):
        start = prediction["predicted_range"]["start_day"]
        end = prediction["predicted_range"]["end_day"]
        facts.append(f"预测经期：{start} 至 {end}")
        if prediction.get("overdue_days"):
            facts.append(f"今天仍未记录新的开始日，已顺延 {prediction['overdue_days']} 天")
    if prediction.get("ovulation_day"):
        facts.append(f"预计排卵日：{prediction['ovulation_day']}（估算）")
    if prediction.get("fertile_window"):
        facts.append(
            f"易孕期：{prediction['fertile_window']['start_day']} 至 "
            f"{prediction['fertile_window']['end_day']}（估算）"
        )
    facts.extend(feeling_facts)
    return facts


def _fallback(data: dict, phase: str) -> tuple[str, dict[str, list[str]], list[str]]:
    """规则文案：不联网时使用，模型失败时也用它兜底。"""

    prediction = data["prediction"]
    overdue = prediction.get("overdue_days") or 0
    cautions = ["排卵日与易孕期为估算，不用于避孕或备孕判断。"]
    if overdue:
        cautions.append("推迟超过一周，或伴异常出血、腹痛，请就医。")

    if overdue:
        summary = (
            "已过原预计日期，月历暂不显示新的预计区间。"
            "补记实际开始日后，预测与排卵日都会重新计算。"
        )
        return summary, {
            "diet": ["正常均衡饮食，不必刻意节食或进补", "少熬夜、少浓咖啡，帮助稳定情绪"],
            "exercise": ["散步、瑜伽等轻中强度活动，按感受来", "明显腹痛或头晕时先休息"],
            "wellbeing": ["先确认是否已经开始，及时补记实际日期", "有性生活且推迟，可先做早孕检测"],
        }, cautions

    if phase == "menstrual" or data["status"].get("in_period"):
        index = data["status"].get("day_index") or 1
        summary = f"今天是经期第 {index} 天，按你记录的日期整理，这几天以休息和保暖为主。"
        return summary, {
            "diet": ["红肉、动物血或深绿叶菜配维C水果，帮助补铁", "温热食物为主，少冰饮与浓咖啡", "三餐规律，主食别省略"],
            "exercise": ["散步或舒缓拉伸 15~20 分钟", "避免大重量与长时间高强度", "以不加重腹痛和疲乏为准"],
            "wellbeing": ["下腹热敷 15 分钟，注意保暖", "把经量与疼痛记进当天感受", "尽量睡够 7 小时"],
        }, cautions + ["经量骤增、持续剧痛或头晕乏力时请就医。"]

    if phase == "ovulatory":
        ovulation = prediction.get("ovulation_day")
        window = prediction.get("fertile_window")
        summary = "按最近周期估算，现在是易孕期"
        if ovulation:
            summary += f"，预计排卵日在 {ovulation[5:7].lstrip('0')} 月 {ovulation[8:].lstrip('0')} 日"
        if window:
            summary += f"，易孕期到 {window['end_day'][5:7].lstrip('0')} 月 {window['end_day'][8:].lstrip('0')} 日前后"
        summary += "。这只是推算，不能当作受孕或避孕依据。"
        return summary, {
            "diet": ["清淡少盐，优质蛋白配坚果与深色蔬菜", "日常饮食即可，不必额外进补"],
            "exercise": ["中等强度有氧或力量训练都可以", "运动后注意补水与拉伸"],
            "wellbeing": ["观察记录白带与基础体温变化", "作息尽量固定，少熬夜"],
        }, cautions

    if phase == "luteal":
        summary = "现在是黄体期，腹胀、乳房胀痛或情绪波动都比较常见，按感受调整强度即可。"
        return summary, {
            "diet": ["少盐少糖，主食配足蛋白，减轻水肿感", "奶类、豆制品、深绿叶菜补充钙镁"],
            "exercise": ["规律有氧配舒缓拉伸，强度按感受下调", "睡前拉伸放松，帮助入睡"],
            "wellbeing": ["把腹胀、情绪记进当天感受", "连续失眠或情绪明显低落可咨询医生"],
        }, cautions

    if phase == "follicular":
        summary = "经期刚结束，卵泡期精力通常在回升，适合把日常活动规律起来。"
        return summary, {
            "diet": ["蛋白质配全谷物，蔬果每天换颜色", "少糖少油，三餐规律更容易坚持"],
            "exercise": ["可以安排力量训练或稍快的快走", "每周 2~3 次、每次 20~30 分钟"],
            "wellbeing": ["记录基础体温或白带变化便于对照", "作息稳定，别把熬夜补在周末"],
        }, cautions

    summary = "记录几次经期开始日后，小结会更贴合你的周期。"
    return summary, {
        "diet": ["均衡三餐，保证蛋白、蔬果和主食", "日常少糖少油即可，不必刻意忌口"],
        "exercise": ["每周 2~3 次中等强度活动，如快走、瑜伽", "从能坚持的时长开始"],
        "wellbeing": ["记下经期开始与结束日期", "同时记录经量与身体感受"],
    }, []


def _headline(data: dict, phase: str, today: date) -> str:
    prediction = data["prediction"]
    status = data["status"]
    if status.get("in_period"):
        return f"经期第 {status['day_index']} 天"
    overdue = prediction.get("overdue_days") or 0
    if overdue:
        return f"已过原预计日期 {overdue} 天"
    if phase == "ovulatory":
        window = prediction.get("fertile_window")
        if window:
            index = (today - date.fromisoformat(window["start_day"])).days + 1
            return f"易孕期第 {index} 天"
        return "易孕期（估算）"
    start = prediction.get("predicted_range", {}).get("start_day") if prediction.get("predicted_range") else None
    if start:
        days = (date.fromisoformat(start) - today).days
        return f"距预计经期 {days} 天" if days >= 0 else "预计经期"
    return "记录几次后开始小结"


def insight(session: Session, customer_id: str, refresh: bool = False) -> CycleInsightOut:
    today = local_today()
    raw = period_service.list_periods(session, customer_id)
    data = _normalize(raw)
    phase_day = cycle_context.current_phase(session, customer_id, today)
    phase = phase_day.phase
    basis = phase_day.basis

    signature = "|".join([
        customer_id,
        today.isoformat(),
        phase,
        basis,
        str(data["prediction"].get("predicted_range")),
        str(data["prediction"].get("overdue_days")),
        str(len(data["items"])),
        str(data["items"][0]["start_day"] if data["items"] else ""),
    ])
    now = time.time()
    cached = _CACHE.get(signature)
    if cached and not refresh and cached[0] > now:
        return cached[1]

    feeling_facts, feeling_summary = _feeling_facts(session, customer_id, today)
    facts = _facts(data, phase, basis, feeling_facts, today)
    fallback = _fallback(data, phase)
    summary, groups, cautions, model_id, demo, degraded = period_ai.build_insight(facts, fallback)
    if feeling_summary and "感受" not in summary:
        summary = f"{summary.rstrip('。')}；最近的记录里{feeling_summary}。"

    payload = CycleInsightOut(
        day=today,
        phase=phase,
        phase_label=PHASE_LABELS[phase],
        basis=basis,
        headline=_headline(data, phase, today),
        summary=summary,
        groups=[
            InsightGroupOut(key=key, title=title, items=groups.get(key, []))
            for key, title in period_ai.GROUP_TITLES
        ],
        cautions=cautions,
        model_id=model_id,
        demo_sample=demo,
        degraded=degraded,
        generated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    _CACHE[signature] = (now + CACHE_TTL_SECONDS, payload)
    return payload
