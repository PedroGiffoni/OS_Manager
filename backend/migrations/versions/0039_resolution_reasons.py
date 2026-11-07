"""Persist a structured resolution for completed cards."""

from alembic import op
import sqlalchemy as sa


revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("resolution", sa.String(length=40), nullable=True))
        batch_op.create_check_constraint(
            "ck_task_resolution_allowed",
            "resolution IS NULL OR resolution IN ('Done', 'Fixed', 'Duplicate', 'Won''t Do', 'Cannot Reproduce', 'Other')",
        )
    op.create_index("ix_tasks_resolution", "tasks", ["resolution"])
    tasks = sa.table("tasks", sa.column("status", sa.String()), sa.column("resolution", sa.String()))
    columns = sa.table("kanban_columns", sa.column("key", sa.String()), sa.column("category", sa.String()))
    done_statuses = sa.select(columns.c.key).where(columns.c.category == "done")
    op.get_bind().execute(
        tasks.update().where(tasks.c.status.in_(done_statuses)).values(resolution="Done")
    )


def downgrade():
    op.drop_index("ix_tasks_resolution", table_name="tasks")
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint("ck_task_resolution_allowed", type_="check")
        batch_op.drop_column("resolution")
