from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import invalid
from app.models.herlog import Feeling
from app.schemas.herlog import FeelingIn, FeelingOut


def _to_out(row: Feeling) -> FeelingOut:
    return FeelingOut(
        day=row.day,
        flow=row.flow,
        symptoms=list(row.symptoms or []),
        impact=row.impact,
        note=row.note,
    )


def list_feelings(session: Session, customer_id: str, day_from: date, day_to: date) -> list[FeelingOut]:
    rows = session.scalars(
        select(Feeling)
        .where(Feeling.customer_id == customer_id, Feeling.day >= day_from, Feeling.day <= day_to)
        .order_by(Feeling.day)
    ).all()
    return [_to_out(row) for row in rows]


def upsert_feeling(session: Session, customer_id: str, day: date, payload: FeelingIn) -> FeelingOut | None:
    """按日覆盖；全部字段清空时等同于删除该日感受。"""

    row = session.scalar(
        select(Feeling).where(Feeling.customer_id == customer_id, Feeling.day == day)
    )
    if payload.is_empty:
        if row is not None:
            session.delete(row)
            session.commit()
        return None
    if payload.symptoms and not isinstance(payload.symptoms, list):  # pragma: no cover - 防御
        raise invalid("症状需为列表")
    if row is None:
        row = Feeling(customer_id=customer_id, day=day)
        session.add(row)
    row.flow = payload.flow
    row.symptoms = payload.symptoms
    row.impact = payload.impact
    row.note = payload.note
    session.commit()
    return _to_out(row)


def delete_feeling(session: Session, customer_id: str, day: date) -> None:
    row = session.scalar(
        select(Feeling).where(Feeling.customer_id == customer_id, Feeling.day == day)
    )
    if row is not None:
        session.delete(row)
        session.commit()
