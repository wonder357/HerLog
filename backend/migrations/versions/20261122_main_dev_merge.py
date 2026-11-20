"""Merge the two feature lines and carry forward existing conversations and likes."""

import sqlalchemy as sa
from alembic import op

revision = "herlog_20261122_main_dev"
down_revision = ("herlog_20261120_chat_history", "herlog_20261122_body_composition")
branch_labels = None
depends_on = None

WEIGHT = "qwhealth_herlog_weight"
OLD_CHECK = "ck_herlog_body_fat_range"
NEW_CHECK = "ck_herlog_weight_body_fat"
LEGACY_PREFIX = "1e9ac00000000000"


def upgrade() -> None:
    if op.get_context().as_sql:
        return
    bind = op.get_bind()
    checks = sa.inspect(bind).get_check_constraints(WEIGHT)
    if any(check["name"] == OLD_CHECK for check in checks):
        with op.batch_alter_table(WEIGHT) as batch:
            batch.drop_constraint(OLD_CHECK, type_="check")
            batch.alter_column("body_fat_pct", existing_type=sa.Numeric(4, 1), type_=sa.Numeric(5, 2))
            batch.create_check_constraint(NEW_CHECK, "body_fat_pct > 0 AND body_fat_pct < 100")

    metadata = sa.MetaData()
    reactions = sa.Table("qwhealth_herlog_discussion_reaction", metadata, autoload_with=bind)
    likes = sa.Table("qwhealth_herlog_discussion_like", metadata, autoload_with=bind)
    shares = sa.Table("qwhealth_herlog_group_share", metadata, autoload_with=bind)
    bind.execute(likes.insert().from_select(
        ["share_id", "customer_id", "created_at"],
        sa.select(reactions.c.share_id, reactions.c.customer_id, shares.c.published_at)
        .join(shares, shares.c.id == reactions.c.share_id)
        .where(reactions.c.kind == "like", ~sa.select(likes.c.share_id).where(
            likes.c.share_id == reactions.c.share_id, likes.c.customer_id == reactions.c.customer_id,
        ).exists()),
    ))

    chats = sa.Table("qwhealth_herlog_assistant_chat", metadata, autoload_with=bind)
    messages = sa.Table("qwhealth_herlog_assistant_message", metadata, autoload_with=bind)
    conversations = sa.Table("qwhealth_herlog_assistant_conversation", metadata, autoload_with=bind)
    turns = sa.Table("qwhealth_herlog_assistant_turn", metadata, autoload_with=bind)
    for chat in bind.execute(sa.select(chats)).mappings().all():
        conversation_id = f"{LEGACY_PREFIX}{chat['id']:016x}"
        if bind.scalar(sa.select(conversations.c.id).where(conversations.c.id == conversation_id)):
            continue
        bind.execute(conversations.insert().values(
            id=conversation_id, title=chat["title"][:24], customer_id=chat["customer_id"],
            created_at=chat["created_at"], updated_at=chat["updated_at"],
        ))
        exchange = None
        for message in bind.execute(sa.select(messages).where(
            messages.c.chat_id == chat["id"], messages.c.customer_id == chat["customer_id"],
        ).order_by(messages.c.id)).mappings().all():
            if message["role"] == "user":
                exchange = message
                continue
            if exchange is None:
                continue
            source = message["source"] if message["source"] in {"records", "deepseek", "fixture"} else "fixture"
            turn_id = f"{exchange['id']:032x}"
            bind.execute(turns.insert().values(
                conversation_id=conversation_id, client_turn_id=turn_id, attempt_id=turn_id,
                question=exchange["content"][:500], mode="records" if source == "records" else "general",
                status="complete", source=source,
                answer={"answer": message["content"], "domain": "general", "range": {"label": "未指定范围"}},
            ))
            exchange = None


def downgrade() -> None:
    # Historical data is retained when the two revision heads are split.
    pass
