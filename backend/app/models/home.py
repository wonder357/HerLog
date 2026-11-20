import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HomePreference(Base):
    __tablename__ = "qwhealth_herlog_home_preference"

    customer_id: Mapped[str] = mapped_column(
        sa.String(32), sa.ForeignKey("qwhealth_member_auth.customer_id"), primary_key=True
    )
    period_reminder_enabled: Mapped[bool] = mapped_column(nullable=False, server_default=sa.false())
    record_reminder_enabled: Mapped[bool] = mapped_column(nullable=False, server_default=sa.false())
    weekly_record_days_target: Mapped[int | None] = mapped_column(sa.SmallInteger)
    show_focus: Mapped[bool] = mapped_column(nullable=False, server_default=sa.true())
    show_summary: Mapped[bool] = mapped_column(nullable=False, server_default=sa.true())
    show_questions: Mapped[bool] = mapped_column(nullable=False, server_default=sa.true())
    password_attempt_count: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False, server_default="0")
    password_attempt_window: Mapped[int | None] = mapped_column(sa.BigInteger)
