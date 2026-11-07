"""Add selectable weekly recurrence to scheduled automation rules."""

from alembic import op
import sqlalchemy as sa


revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("automation_rules") as batch_op:
        batch_op.add_column(
            sa.Column("schedule_frequency", sa.String(length=10), nullable=False, server_default="daily")
        )
        batch_op.add_column(
            sa.Column("schedule_weekdays", sa.JSON(), nullable=False, server_default="[]")
        )


def downgrade():
    # Do not silently convert weekly rules into daily schedules on rollback.
    op.execute(
        "UPDATE automation_rules SET enabled = 0 WHERE schedule_frequency = 'weekly'"
    )
    with op.batch_alter_table("automation_rules") as batch_op:
        batch_op.drop_column("schedule_weekdays")
        batch_op.drop_column("schedule_frequency")
