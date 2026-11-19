"""只读问答：先定模块与日期范围，再按当前会员取允许读取的字段。

回答和记录引用由服务端根据已保存事实生成。
"""

from __future__ import annotations

import re
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.clock import local_today
from app.schemas.herlog import AssistantAnswerOut, AssistantRange, AssistantTopic, RecordRef
from app.services import period_service, skin_service, weight_service

WEIGHT_WORDS = ("体重", "kg", "公斤", "斤", "称重", "瘦", "胖", "重量")
PERIOD_WORDS = ("经期", "月经", "周期", "姨妈", "经量", "腹痛")
SKIN_WORDS = ("皮肤", "痘", "脸", "黑头", "泛红", "毛孔", "色斑")
RECORD_WORDS = ("帮我记", "记一笔", "记下", "记录一下", "帮我添加", "录入")

WEIGHT_ROUTE = "/pages/weight/index"
PERIOD_ROUTE = "/pages/period/index"
SKIN_ROUTE = "/pages/skin/index"


def _hits(question: str, words: tuple[str, ...]) -> bool:
    lowered = question.lower()
    return any(word in lowered for word in words)


def _days_from_question(question: str, default: int) -> int:
    if any(token in question for token in ("30 天", "30天", "一个月", "近一月", "整整一月")):
        return 30
    if any(token in question for token in ("7 天", "7天", "一周", "这周", "七天", "这星期", "本周")):
        return 7
    return default


def _kg(grams: int | None) -> str:
    if grams is None:
        return "—"
    return f"{grams / 1000:.3f}".rstrip("0").rstrip(".")


def _resolve_follow_up(question: str, topic: AssistantTopic | None) -> str:
    """只承接可识别的简短追问，所有记录仍由本次登录账号读取。"""

    phrase = re.sub(r"[\s？?。！!，,]+", "", question)
    phrase = re.sub(r"^那(?:么)?|(?:呢|吗)$", "", phrase)
    if topic == "weight":
        if re.fullmatch(r"(?:近|最近|过去)?(?:30天|三十天|一个月)", phrase):
            return "最近 30 天体重怎么样"
        if re.fullmatch(r"(?:近|最近|过去)?(?:7天|七天|一周)|这周|本周", phrase):
            return "最近 7 天体重怎么样"
    if topic == "period":
        if phrase in {"上次", "上一次", "最近一次", "最近一次是哪天"}:
            return "最近一次经期从哪天开始"
        if phrase in {"下次", "下一次", "下次大概什么时候", "下次什么时候"}:
            return "下次经期大概什么时候"
    if topic == "skin" and phrase in {"最近一条", "最近一次"}:
        return "最近一次皮肤观察是什么"
    return question


def answer_question(
    session: Session, customer_id: str, question: str, follow_up_topic: AssistantTopic | None = None,
) -> AssistantAnswerOut:
    question = _resolve_follow_up(question, follow_up_topic)
    weight_hit = _hits(question, WEIGHT_WORDS)
    period_hit = _hits(question, PERIOD_WORDS)
    skin_hit = _hits(question, SKIN_WORDS)

    if _hits(question, RECORD_WORDS):
        return AssistantAnswerOut(
            answer=(
                "对话只能读取已保存的记录，不能直接写入。"
                "想记体重请回到首页点「记体重」，记经期点「记经期」，拍照分析在皮肤页。"
            ),
            domain="record_help",
            range=AssistantRange(label="未指定范围"),
            record_refs=[
                RecordRef(type="weight", id="entry", label="记体重", route=WEIGHT_ROUTE),
                RecordRef(type="period", id="entry", label="记经期", route=PERIOD_ROUTE),
                RecordRef(type="skin", id="entry", label="拍照分析", route=SKIN_ROUTE),
            ],
        )

    if sum((weight_hit, period_hit, skin_hit)) >= 2:
        return AssistantAnswerOut(
            answer=(
                "我不会把经期、体重和皮肤记录拼在一起做归因。"
                "你可以先选择要看哪一类记录，我按已保存的数据单独说明。"
            ),
            domain="unsupported",
            range=AssistantRange(label="未指定范围"),
            record_refs=[
                RecordRef(type="period", id="module", label="查看经期记录", route=PERIOD_ROUTE),
                RecordRef(type="skin", id="module", label="查看皮肤观察", route=SKIN_ROUTE),
            ],
        )

    if weight_hit:
        return _weight_answer(session, customer_id, question)
    if period_hit:
        return _period_answer(session, customer_id, question)
    if skin_hit:
        return _skin_answer(session, customer_id)
    return AssistantAnswerOut(
        answer=(
            "我目前能回答体重、经期和皮肤三方面的已保存记录，"
            "比如「这周体重有变化吗」「下次经期大概什么时候」「最近一次皮肤观察是什么」。"
        ),
        domain="unsupported",
        range=AssistantRange(label="未指定范围"),
    )


def _weight_answer(session: Session, customer_id: str, question: str) -> AssistantAnswerOut:
    days = _days_from_question(question, default=7)
    today = local_today()
    start_day = today - timedelta(days=days - 1)
    data = weight_service.summary(session, customer_id, days)
    label = f"最近 {days} 天（{start_day.isoformat()} 至 {today.isoformat()}）"
    if data.count == 0:
        text = f"{label}还没有体重记录。点「记体重」记一笔，之后就能回答变化了。"
    elif data.delta_grams is None:
        text = (
            f"{label}记录了 {data.count} 笔体重，最近一次是 {_kg(data.latest_grams)} kg。"
            "目前只有一天的数据点，还看不出变化，再记几天就能比较。"
        )
    else:
        direction = "增加" if data.delta_grams > 0 else ("减少" if data.delta_grams < 0 else "持平")
        text = (
            f"{label}共 {data.count} 笔记录，按每天最后一次测量取 {len(data.points)} 个数据点，"
            f"从 {_kg(data.points[0].grams)} kg 到 {_kg(data.points[-1].grams)} kg，"
            f"变化 {data.delta_kg:+.3f} kg（{direction}）。"
        )
    refs = [
        RecordRef(
            type="weight",
            id=str(point.weight_id),
            label=f"{point.day.isoformat()} {_kg(point.grams)} kg",
            route=WEIGHT_ROUTE,
        )
        for point in data.points
    ]
    return AssistantAnswerOut(
        answer=text,
        domain="weight",
        range=AssistantRange(label=label, date_from=start_day, date_to=today, days=days),
        record_refs=refs,
    )


def _period_answer(session: Session, customer_id: str, question: str) -> AssistantAnswerOut:
    today = local_today()
    data = period_service.list_periods(session, customer_id)
    rows = data["items"]
    if "最近一次" in question and any(word in question for word in ("哪天", "何时", "什么时候")):
        latest = next((row for row in rows if row.start_day <= today), None)
        return AssistantAnswerOut(
            answer=f"最近一次已记录的经期开始日是 {latest.start_day.isoformat()}。" if latest else "还没有实际经期开始记录。",
            domain="period", range=AssistantRange(label="最近一次实际经期"),
            record_refs=[RecordRef(type="period", id=str(latest.id), label="查看经期记录", route=PERIOD_ROUTE)] if latest else [],
        )
    prediction = data["prediction"]
    if not rows:
        text = "还没有经期记录。补记开始日期后，我会按历史间隔估算下次开始日。"
    elif prediction["status"] == "insufficient":
        text = f"目前有 {len(rows)} 段经期记录。{prediction['message']}。"
    elif prediction["status"] == "irregular":
        text = prediction["message"] + "。本次不给出具体日期，也不据此判断健康状况。"
    elif prediction["status"] == "overdue":
        expected = prediction["expected_start"]
        text = (
            f"按最近记录的间隔估算，预计开始日是 {expected.isoformat()}，"
            "现在已经过了这一天，还没有新的开始记录。可以在经期页补记。"
        )
    else:
        expected = prediction["expected_start"]
        text = (
            f"按最近记录的间隔估算，预计下次开始是 {expected.isoformat()}"
            f"（按约 {prediction['estimate_days']} 天周期）。"
            "这只是根据历史记录的估算，实际日期可能不同，不作为避孕依据。"
        )

    refs = [
        RecordRef(
            type="period",
            id=str(row.id),
            label=f"{row.start_day.isoformat()} 开始",
            route=PERIOD_ROUTE,
        )
        for row in rows[:3]
    ]
    label = "全部经期记录"
    return AssistantAnswerOut(
        answer=text,
        domain="period",
        range=AssistantRange(
            label=label,
            date_from=rows[-1].start_day if rows else None,
            date_to=today,
        ),
        record_refs=refs,
    )


def _skin_answer(session: Session, customer_id: str) -> AssistantAnswerOut:
    rows = skin_service.list_observations(session, customer_id, limit=1)
    if not rows:
        return AssistantAnswerOut(
            answer="还没有保存过皮肤观察。到皮肤页选好部位拍照，确认结果后保存，历史里才会出现。",
            domain="skin",
            range=AssistantRange(label="最近一次已保存观察"),
            record_refs=[RecordRef(type="skin", id="entry", label="拍照分析", route=SKIN_ROUTE)],
        )
    latest = rows[0]
    text = (
        f"最近一次已保存的观察在 {latest.site}。\n"
        f"AI 观察 · 不用于诊断\n{latest.visible}\n"
        "想对比可以到皮肤页历史里挑同一部位的两条记录。"
    )
    if latest.demo_sample:
        text = "演示样例 · 未调用模型推理\n" + text
    return AssistantAnswerOut(
        answer=text,
        domain="skin",
        range=AssistantRange(label="最近一次已保存观察"),
        record_refs=[
            RecordRef(type="skin", id=str(latest.id), label=f"{latest.site} {latest.captured_at}", route=SKIN_ROUTE)
        ],
    )
