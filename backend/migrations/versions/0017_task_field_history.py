"""Normalize task audit field changes for portable history queries."""

import json

from alembic import op
import sqlalchemy as sa


revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _entries(action, details):
    entries = []
    if action == "status_changed" and "origin" in details and "destination" in details:
        entries.append(
            {
                "field": "status",
                "kind": "value",
                "before": details["origin"],
                "after": details["destination"],
            }
        )
    raw_changes = details.get("changes", [])
    if isinstance(raw_changes, list):
        entries.extend(change for change in raw_changes if isinstance(change, dict))
    elif isinstance(raw_changes, dict):
        entries.extend(
            {"field": field, "kind": "value", **change}
            for field, change in raw_changes.items()
            if isinstance(change, dict)
        )
    return entries


def upgrade():
    op.create_table(
        "task_field_changes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "audit_id",
            sa.Integer(),
            sa.ForeignKey("audit_logs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field", sa.String(length=80), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False, server_default="value"),
        sa.Column("before_json", sa.Text(), nullable=False),
        sa.Column("after_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("audit_id", "field", "kind"),
    )
    op.create_index("ix_task_field_changes_audit_id", "task_field_changes", ["audit_id"])
    op.create_index(
        "ix_task_field_changes_field_audit", "task_field_changes", ["field", "audit_id"]
    )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, action, details FROM audit_logs WHERE entity = 'task'")
    ).mappings()
    insert = sa.table(
        "task_field_changes",
        sa.column("audit_id", sa.Integer()),
        sa.column("field", sa.String()),
        sa.column("kind", sa.String()),
        sa.column("before_json", sa.Text()),
        sa.column("after_json", sa.Text()),
    )
    for row in rows:
        details = row["details"] or {}
        if isinstance(details, str):
            details = json.loads(details)
        if not isinstance(details, dict):
            continue
        seen = set()
        for change in _entries(row["action"], details):
            field = change.get("field")
            kind = change.get("kind", "value")
            if (
                not isinstance(field, str)
                or not field
                or "before" not in change
                or "after" not in change
                or (field, kind) in seen
            ):
                continue
            seen.add((field, kind))
            connection.execute(
                insert.insert().values(
                    audit_id=row["id"],
                    field=field,
                    kind=kind,
                    before_json=_canonical(change["before"]),
                    after_json=_canonical(change["after"]),
                )
            )


def downgrade():
    op.drop_index("ix_task_field_changes_field_audit", table_name="task_field_changes")
    op.drop_index("ix_task_field_changes_audit_id", table_name="task_field_changes")
    op.drop_table("task_field_changes")
