"""Backfill searchable aliases for custom field configuration changes."""

import json

from alembic import op
import sqlalchemy as sa


revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def upgrade():
    bind = op.get_bind()
    history = sa.table(
        "task_field_changes",
        sa.column("id", sa.Integer),
        sa.column("audit_id", sa.Integer),
        sa.column("field", sa.String),
        sa.column("kind", sa.String),
        sa.column("before_json", sa.Text),
        sa.column("after_json", sa.Text),
    )
    rows = bind.execute(
        sa.select(
            history.c.audit_id,
            history.c.field,
            history.c.before_json,
            history.c.after_json,
        ).where(history.c.kind == "configuration")
    )
    for row in rows:
        try:
            before, after = json.loads(row.before_json), json.loads(row.after_json)
        except (TypeError, json.JSONDecodeError):
            continue
        if any(value is not None and not isinstance(value, dict) for value in (before, after)):
            continue
        before_config, after_config = before or {}, after or {}
        for prop in sorted(before_config.keys() | after_config.keys()):
            old, new = before_config.get(prop), after_config.get(prop)
            if old == new:
                continue
            alias = f"config_{row.field}_{prop}"
            exists = bind.execute(
                sa.select(history.c.id).where(
                    history.c.audit_id == row.audit_id,
                    history.c.field == alias,
                    history.c.kind == "value",
                ).limit(1)
            ).first()
            if exists:
                continue
            bind.execute(
                history.insert().values(
                    audit_id=row.audit_id,
                    field=alias,
                    kind="configuration_property",
                    before_json=_canonical(old),
                    after_json=_canonical(new),
                )
            )


def downgrade():
    history = sa.table(
        "task_field_changes",
        sa.column("field", sa.String),
        sa.column("kind", sa.String),
    )
    op.get_bind().execute(
        history.delete().where(
            history.c.kind == "configuration_property",
            history.c.field.like(r"config\_%", escape="\\"),
        )
    )
