"""Add encrypted browser push subscriptions and delivery outbox."""

from alembic import op
import sqlalchemy as sa


revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "push_subscriptions",
        sa.Column("endpoint_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("endpoint_hash"),
    )
    op.create_index("ix_push_subscriptions_user", "push_subscriptions", ["user_id"])
    op.create_table(
        "push_outbox",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("subscription_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["notification_id"], ["in_app_notifications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["subscription_hash"], ["push_subscriptions.endpoint_hash"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sending', 'sent', 'skipped', 'failed')",
            name="ck_push_outbox_status",
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_push_outbox_attempts"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "notification_id", "subscription_hash", name="uq_push_outbox_notice_device"
        ),
    )
    op.create_index("ix_push_outbox_due", "push_outbox", ["status", "next_attempt_at"])
    op.create_index("ix_push_outbox_next_attempt_at", "push_outbox", ["next_attempt_at"])


def downgrade():
    op.drop_index("ix_push_outbox_next_attempt_at", table_name="push_outbox")
    op.drop_index("ix_push_outbox_due", table_name="push_outbox")
    op.drop_table("push_outbox")
    op.drop_index("ix_push_subscriptions_user", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
