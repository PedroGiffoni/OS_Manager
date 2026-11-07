"""Add daily UTC automation schedules with durable idempotency."""

from alembic import op
import sqlalchemy as sa


revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("automation_rules", sa.Column("schedule_time", sa.String(length=5), nullable=True))
    op.create_table(
        "automation_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "rule_id",
            sa.Integer(),
            sa.ForeignKey("automation_rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("run_date", sa.String(length=10), nullable=False),
        sa.Column("completed_at", sa.String(), nullable=False),
        sa.UniqueConstraint("rule_id", "run_date", name="uq_automation_run_rule_day"),
    )
    op.create_index("ix_automation_runs_rule_id", "automation_runs", ["rule_id"])


def downgrade():
    op.drop_index("ix_automation_runs_rule_id", table_name="automation_runs")
    op.drop_table("automation_runs")
    op.drop_column("automation_rules", "schedule_time")
