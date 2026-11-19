"""Qiwen member auth baseline that the contest branch pins as its parent head.

Revision ID: h9b0c1d2e3f4
Revises: -
Create Date: 2026-11-18
"""
from alembic import op
import sqlalchemy as sa

revision = "h9b0c1d2e3f4"
down_revision = None
branch_labels = None
depends_on = None

MEMBER = "qwhealth_member_auth"
SESSION = "qwhealth_member_auth_session"


def upgrade():
    """会员表按原样创建：此时 phone 唯一且必填，也还没有 org_id 列。

    紧随其后的 `herlog_20261118` 会把 phone 改为可空并补上 org_id。
    """

    op.create_table(
        MEMBER,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.String(32), nullable=False, unique=True),
        sa.Column("phone", sa.String(20), nullable=False, unique=True),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        SESSION,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "customer_id",
            sa.String(32),
            sa.ForeignKey(f"{MEMBER}.customer_id"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_member_auth_session_customer", SESSION, ["customer_id"])


def downgrade():
    op.drop_index("ix_member_auth_session_customer", table_name=SESSION)
    op.drop_table(SESSION)
    op.drop_table(MEMBER)
