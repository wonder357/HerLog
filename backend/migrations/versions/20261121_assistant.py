"""首页智能体的对话与消息。"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "herlog_20261121_assistant"
down_revision = "herlog_20261120_photos"
branch_labels = None
depends_on = None

CHAT = "qwhealth_herlog_assistant_chat"
CONVERSATION = "qwhealth_herlog_assistant_conversation"
MESSAGE = "qwhealth_herlog_assistant_message"
MEMBER = "qwhealth_member_auth.customer_id"
ROW_ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    context = op.get_context()
    if not context.as_sql:
        inspector = sa.inspect(op.get_bind())
        if inspector.has_table(CHAT) and any(column["name"] == "deleted_at" for column in inspector.get_columns(CHAT)):
            op.rename_table(CHAT, CONVERSATION)
    if context.dialect.name == "mysql":
        op.alter_column("alembic_version", "version_num", existing_type=sa.String(32),
                        type_=sa.String(64), existing_nullable=False)
    op.create_table(
        CHAT,
        sa.Column("id", ROW_ID, primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.String(32), sa.ForeignKey(MEMBER), nullable=False),
        sa.Column("title", sa.String(60), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=3), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=3), nullable=False),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_herlog_assistant_chat_owner", CHAT, ["customer_id", "updated_at", "id"])
    op.create_table(
        MESSAGE,
        sa.Column("id", ROW_ID, primary_key=True, autoincrement=True),
        sa.Column(
            "chat_id", ROW_ID, sa.ForeignKey(f"{CHAT}.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("customer_id", sa.String(32), sa.ForeignKey(MEMBER), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(16), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=3), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_herlog_assistant_role"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_herlog_assistant_message_chat", MESSAGE, ["chat_id", "id"])


def downgrade() -> None:
    op.drop_table(MESSAGE)
    op.drop_table(CHAT)
