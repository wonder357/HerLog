from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有比赛分支 ORM 的声明基类；Alembic 以 Base.metadata 生成迁移对比。"""
