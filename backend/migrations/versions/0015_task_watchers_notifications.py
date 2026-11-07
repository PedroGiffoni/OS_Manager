"""Add task watchers and in-app notifications."""

from alembic import op
import sqlalchemy as sa


revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "task_watchers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.UniqueConstraint("task_id", "user_id"),
    )
    op.create_index("ix_task_watchers_task_id", "task_watchers", ["task_id"])
    op.create_index("ix_task_watchers_user_id", "task_watchers", ["user_id"])
    op.create_table(
        "in_app_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("read_at", sa.String(), nullable=True),
    )
    op.create_index("ix_in_app_notifications_user_id", "in_app_notifications", ["user_id"])
    op.create_index("ix_in_app_notifications_task_id", "in_app_notifications", ["task_id"])
    op.create_index("ix_in_app_notifications_created_at", "in_app_notifications", ["created_at"])


def downgrade():
    op.drop_index("ix_in_app_notifications_created_at", table_name="in_app_notifications")
    op.drop_index("ix_in_app_notifications_task_id", table_name="in_app_notifications")
    op.drop_index("ix_in_app_notifications_user_id", table_name="in_app_notifications")
    op.drop_table("in_app_notifications")
    op.drop_index("ix_task_watchers_user_id", table_name="task_watchers")
    op.drop_index("ix_task_watchers_task_id", table_name="task_watchers")
    op.drop_table("task_watchers")
