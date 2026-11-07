"""Add personal scheduled filter subscriptions and in-app match notifications."""

from alembic import op
import sqlalchemy as sa


revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "in_app_notifications",
        sa.Column("source_label", sa.String(length=120), nullable=False, server_default=""),
    )
    op.create_table(
        "filter_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("frequency", sa.String(length=10), nullable=False, server_default="daily"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("next_run_at", sa.String(), nullable=False),
        sa.Column("last_run_at", sa.String(), nullable=True),
        sa.Column("last_error", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.CheckConstraint(
            "frequency IN ('daily', 'weekly')", name="ck_filter_subscription_frequency"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "name", name="uq_filter_subscription_user_name"),
    )
    op.create_index("ix_filter_subscriptions_user_id", "filter_subscriptions", ["user_id"])
    op.create_index("ix_filter_subscriptions_active", "filter_subscriptions", ["active"])
    op.create_index("ix_filter_subscriptions_next_run_at", "filter_subscriptions", ["next_run_at"])
    op.create_index(
        "ix_filter_subscriptions_due", "filter_subscriptions", ["active", "next_run_at"]
    )
    op.create_table(
        "filter_subscription_matches",
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("matched_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["filter_subscriptions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("subscription_id", "task_id"),
    )
    op.create_index(
        "ix_filter_subscription_matches_task", "filter_subscription_matches", ["task_id"]
    )


def downgrade():
    op.drop_index("ix_filter_subscription_matches_task", table_name="filter_subscription_matches")
    op.drop_table("filter_subscription_matches")
    op.drop_index("ix_filter_subscriptions_due", table_name="filter_subscriptions")
    op.drop_index("ix_filter_subscriptions_next_run_at", table_name="filter_subscriptions")
    op.drop_index("ix_filter_subscriptions_active", table_name="filter_subscriptions")
    op.drop_index("ix_filter_subscriptions_user_id", table_name="filter_subscriptions")
    op.drop_table("filter_subscriptions")
    with op.batch_alter_table("in_app_notifications") as batch_op:
        batch_op.drop_column("source_label")
