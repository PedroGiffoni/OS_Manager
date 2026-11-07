"""Add optional SCM and deployment event links for work cards."""

from alembic import op
import sqlalchemy as sa


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "development_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("delivery_id", sa.String(length=160), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("actor", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("occurred_at", sa.String(), nullable=True),
        sa.Column("received_at", sa.String(), nullable=False),
        sa.UniqueConstraint("provider", "delivery_id", "task_id"),
    )
    op.create_index("ix_development_events_provider", "development_events", ["provider"])
    op.create_index("ix_development_events_task_id", "development_events", ["task_id"])


def downgrade():
    op.drop_table("development_events")
