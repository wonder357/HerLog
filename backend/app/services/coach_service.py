"""AI 教练：把服务端算好的事实交给模型解释，离线时用同一批事实拼固定文案。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.clock import local_today
from app.core.config import settings
from app.logic import metabolism
from app.schemas.weight_plus import (
    CoachChatOut,
    CoachReportOut,
    KnowledgeRefOut,
)
from app.services import goal_service, knowledge, meal_service, weight_ai, weight_service

RECORD_WORDS = ("帮我记", "记录一下", "记一笔", "录入", "添加")


def _kg(grams: int | None) -> str:
    if grams is None:
        return "—"
    return f"{grams / 1000:.3f}".rstrip("0").rstrip(".")


def _facts(session: Session, customer_id: str, days: int) -> tuple[list[str], dict]:
    today = local_today()
    summary = weight_service.summary(session, customer_id, days)
    goal = goal_service.goal_state(session, customer_id)
    recorded_days, avg_kcal = meal_service.week_average_kcal(session, customer_id, days)
    points = [(point.day, point.grams) for point in summary.points]
    streak = metabolism.streak_days([day for day, _ in points], today)
    avg = metabolism.moving_average([grams for _, grams in points])

    facts = [
        f"今天：{today.isoformat()}",
        f"统计范围：最近 {days} 天，共 {summary.count} 笔记录、{len(summary.points)} 个数据点",
        f"最近一次体重：{_kg(summary.latest_grams)} kg",
    ]
    if summary.delta_grams is not None:
        facts.append(
            f"首尾变化：{summary.delta_kg:+.3f} kg（{summary.points[0].day.isoformat()} 至 "
            f"{summary.points[-1].day.isoformat()}）"
        )
    if avg is not None:
        facts.append(f"数据点均值：{avg / 1000:.2f} kg")
    facts.append(f"连续记录：{streak} 天")
    if goal.has_goal:
        facts.append(
            f"目标体重：{goal.target_kg} kg，已完成 {goal.percent}%，还差 {goal.remaining_kg} kg"
            + (f"，按当前趋势预计 {goal.forecast_day} 到达" if goal.forecast_day else "")
        )
    else:
        facts.append("目标体重：未设置")
    if goal.intake_target_kcal is not None:
        facts.append(f"每日摄入目标：约 {goal.intake_target_kcal} kcal（轻度活动估算）")
    if recorded_days:
        facts.append(f"饮食记录：最近 {days} 天有 {recorded_days} 天记录，日均 {avg_kcal} kcal")
    else:
        facts.append("饮食记录：最近没有任何记录")
    if goal.bmi.value is not None:
        facts.append(f"BMI：{goal.bmi.value}（{goal.bmi.category}）")
    return facts, {
        "summary": summary,
        "goal": goal,
        "streak": streak,
        "avg_kcal": avg_kcal,
        "recorded_days": recorded_days,
        "avg_grams": avg,
    }


def _fallback(summary, goal, recorded_days: int, days: int) -> tuple[str, list[str], list[str]]:
    if summary.count == 0:
        text = f"最近 {days} 天还没有体重记录，先记一笔才能看趋势。"
    elif len(summary.points) <= 1:
        text = (
            f"最近 {days} 天记录了 {summary.count} 笔，目前只有 {len(summary.points)} 个数据点，"
            "再记几天就能比较趋势。"
        )
    else:
        direction = "下降" if (summary.delta_grams or 0) < 0 else ("上升" if (summary.delta_grams or 0) > 0 else "持平")
        text = (
            f"最近 {days} 天记录了 {summary.count} 笔，按每天最后一次取 {len(summary.points)} 个点，"
            f"从 {_kg(summary.points[0].grams)} kg 到 {_kg(summary.points[-1].grams)} kg，"
            f"变化 {summary.delta_kg:+.3f} kg（{direction}）。"
        )

    highlights: list[str] = []
    if summary.count >= max(3, days // 2):
        highlights.append(f"这一段时间记录了 {summary.count} 次，数据足够看出趋势。")
    if recorded_days:
        highlights.append(f"有 {recorded_days} 天记录了饮食，热量记录会越来越准。")
    if goal.has_goal and goal.percent > 0:
        highlights.append(f"目标进度 {goal.percent}%，已经走过去的一部分。")

    cautions: list[str] = []
    if summary.count and len(summary.points) < max(3, days // 2):
        cautions.append("数据点偏少，单次波动会被放大，尽量在相近条件下称重。")
    if goal.slope_kg_per_week is not None and goal.slope_kg_per_week < -1.0:
        cautions.append("按记录推算每周下降超过 1 kg，速度偏快，注意蛋白质和主食别一起砍。")
    if goal.bmi.value is None:
        cautions.append("补全身高后可以算出 BMI 和个人热量目标。")
    if not goal.has_goal:
        cautions.append("还没设置目标体重，进度与预测日期需要目标才能算。")
    return text, highlights[:3], cautions[:3]


def report(session: Session, customer_id: str, days: int = 7) -> CoachReportOut:
    if days not in (7, 30):
        days = 7
    facts, extra = _facts(session, customer_id, days)
    summary, highlights, cautions = _fallback(
        extra["summary"], extra["goal"], extra["recorded_days"], days
    )
    text, good, caution, model_id, demo = weight_ai.coach_report(
        facts, (summary, highlights, cautions)
    )
    return CoachReportOut(
        range_label=f"最近 {days} 天",
        summary=text,
        highlights=good,
        cautions=caution,
        facts=facts,
        model_id=model_id,
        demo_sample=demo,
    )


def chat(session: Session, customer_id: str, question: str) -> CoachChatOut:
    facts, extra = _facts(session, customer_id, 7)
    summary = extra["summary"]
    hits = knowledge.search(question)

    if any(word in question for word in RECORD_WORDS):
        fallback = (
            "对话只能读已保存的记录，不能直接写入。想记体重点「记体重」，想记饮食点「记饮食」。"
        )
    elif hits:
        tail = (
            f"你最近一次记录是 {_kg(summary.latest_grams)} kg。"
            if summary.latest_grams is not None
            else "你还没有体重记录。"
        )
        fallback = f"{hits[0].summary} {tail}"
    elif summary.count == 0:
        fallback = "最近还没有体重记录，先记一笔，我就能按数据回答趋势和目标进度。"
    elif summary.delta_grams is None:
        fallback = (
            f"最近 7 天记录了 {summary.count} 笔，最近一次是 {_kg(summary.latest_grams)} kg。"
            "目前只有一个数据点，还看不出变化。"
        )
    else:
        fallback = (
            f"最近 7 天从 {_kg(summary.points[0].grams)} kg 到 {_kg(summary.points[-1].grams)} kg，"
            f"变化 {summary.delta_kg:+.3f} kg。"
            + (f"目标还差 {extra['goal'].remaining_kg} kg。" if extra["goal"].has_goal else "")
        )

    answer, cited, model_id, demo = weight_ai.coach_chat(facts, question, fallback)
    return CoachChatOut(
        answer=answer,
        facts=[] if demo else facts,
        knowledge=[KnowledgeRefOut(slug=topic.slug, title=topic.title) for topic in cited],
        model_id=model_id or settings.HERLOG_MODEL_ID,
        demo_sample=demo,
    )
