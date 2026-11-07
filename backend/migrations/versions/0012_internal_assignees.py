"""Assign cards to an internal owner for resource capacity analysis."""

from alembic import op
import sqlalchemy as sa


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
        "tasks",
        table_args=(
            sa.CheckConstraint(
                "estimated_minutes >= 0 AND used_minutes >= 0",
                name="ck_task_hours_nonnegative",
            ),
            sa.CheckConstraint(
                "parent_id IS NULL OR parent_id != id",
                name="ck_task_not_own_parent",
            ),
        ),
    ) as batch:
        batch.add_column(sa.Column("assignee_user_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_tasks_assignee_user", "users", ["assignee_user_id"], ["id"]
        )
        batch.create_index("ix_tasks_assignee_user_id", ["assignee_user_id"])


def downgrade():
    with op.batch_alter_table(
        "tasks",
        table_args=(
            sa.CheckConstraint(
                "estimated_minutes >= 0 AND used_minutes >= 0",
                name="ck_task_hours_nonnegative",
            ),
            sa.CheckConstraint(
                "parent_id IS NULL OR parent_id != id",
                name="ck_task_not_own_parent",
            ),
        ),
    ) as batch:
        batch.drop_index("ix_tasks_assignee_user_id")
        batch.drop_constraint("fk_tasks_assignee_user", type_="foreignkey")
        batch.drop_column("assignee_user_id")
