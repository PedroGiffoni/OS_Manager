"""Persist ordered allowlisted action sequences for automation rules."""

from alembic import op
import sqlalchemy as sa


revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "automation_rules",
        sa.Column("actions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    bind = op.get_bind()
    table = sa.table(
        "automation_rules",
        sa.column("id", sa.Integer),
        sa.column("action", sa.String),
        sa.column("config", sa.JSON),
        sa.column("actions", sa.JSON),
    )
    rows = bind.execute(sa.select(table.c.id, table.c.action, table.c.config, table.c.actions))
    for row in rows:
        sequence = row.actions or [{"action": row.action, "config": row.config or {}}]
        bind.execute(
            table.update().where(table.c.id == row.id).values(actions=sequence)
        )


def downgrade():
    bind = op.get_bind()
    table = sa.table(
        "automation_rules",
        sa.column("id", sa.Integer),
        sa.column("action", sa.String),
        sa.column("config", sa.JSON),
        sa.column("actions", sa.JSON),
    )
    rows = bind.execute(sa.select(table.c.id, table.c.actions))
    for row in rows:
        actions = row.actions or []
        if len(actions) > 1:
            raise RuntimeError(
                "Não é possível rebaixar a migração: uma regra contém múltiplas ações. "
                "Reduza a sequência para uma ação antes do downgrade."
            )
        first = actions[0] if actions else {}
        if first.get("action") and isinstance(first.get("config"), dict):
            bind.execute(
                table.update()
                .where(table.c.id == row.id)
                .values(action=first["action"], config=first["config"])
            )
    op.drop_column("automation_rules", "actions")
