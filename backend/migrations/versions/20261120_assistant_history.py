"""Add opt-in, account-scoped assistant conversation history."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "herlog_20261120_chat_history"
down_revision = "herlog_20261120_body_fat"
branch_labels = None
depends_on = None

HOME = "qwhealth_herlog_home_preference"
CHAT = "qwhealth_herlog_assistant_chat"
TURN = "qwhealth_herlog_assistant_turn"
MOMENT = sa.DateTime().with_variant(mysql.DATETIME(fsp=3), "mysql")


def upgrade() -> None:
    op.add_column(HOME, sa.Column("assistant_history_enabled", sa.Boolean(), nullable=True))
    op.create_table(
        CHAT,
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("customer_id", sa.String(32), sa.ForeignKey("qwhealth_member_auth.customer_id"), nullable=False),
        sa.Column("title", sa.String(24), nullable=False),
        sa.Column("created_at", MOMENT, nullable=False),
        sa.Column("updated_at", MOMENT, nullable=False),
        sa.Column("deleted_at", MOMENT),
    )
    op.create_index("ix_herlog_assistant_history", CHAT, ["customer_id", "deleted_at", "updated_at", "id"])
    op.create_table(
        TURN,
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("conversation_id", sa.String(32), sa.ForeignKey(f"{CHAT}.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_turn_id", sa.String(32), nullable=False),
        sa.Column("attempt_id", sa.String(32), nullable=False),
        sa.Column("question", sa.String(500), nullable=False),
        sa.Column("mode", sa.String(8), nullable=False),
        sa.Column("topic", sa.String(8)),
        sa.Column("status", sa.String(9), nullable=False),
        sa.Column("source", sa.String(8)),
        sa.Column("answer", sa.JSON(none_as_null=True)),
        sa.Column("partial", sa.Text()),
        sa.Column("error", sa.String(200)),
        sa.UniqueConstraint("conversation_id", "client_turn_id", name="uq_herlog_assistant_client_turn"),
    )
    op.create_index("ix_herlog_assistant_turn_order", TURN, ["conversation_id", "id"])


def downgrade() -> None:
    op.drop_table(TURN)
    op.drop_table(CHAT)
    op.drop_column(HOME, "assistant_history_enabled")
