import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.herlog import PROFILE_TABLE, WEIGHT_TABLE, _ROW_ID
from app.models.wellness import Checkin


class PhotoColumns:
    image_bytes: Mapped[bytes] = mapped_column(
        sa.LargeBinary().with_variant(mysql.MEDIUMBLOB(), "mysql"), nullable=False, deferred=True
    )
    digest: Mapped[str] = mapped_column(sa.String(64), nullable=False)


class WeightPhoto(PhotoColumns, Base):
    __tablename__ = "qwhealth_herlog_weight_photo"

    record_id: Mapped[int] = mapped_column(_ROW_ID, sa.ForeignKey(f"{WEIGHT_TABLE}.id", ondelete="CASCADE"), primary_key=True)


class CheckinPhoto(PhotoColumns, Base):
    __tablename__ = "qwhealth_herlog_checkin_photo"

    record_id: Mapped[int] = mapped_column(
        _ROW_ID, sa.ForeignKey(f"{Checkin.__tablename__}.id", ondelete="CASCADE"), primary_key=True
    )


class ProfilePhoto(PhotoColumns, Base):
    __tablename__ = "qwhealth_herlog_profile_photo"

    record_id: Mapped[str] = mapped_column(
        sa.String(32), sa.ForeignKey(f"{PROFILE_TABLE}.customer_id", ondelete="CASCADE"), primary_key=True
    )
