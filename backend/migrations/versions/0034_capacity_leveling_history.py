"""Persist versioned capacity leveling scenarios."""

from alembic import op
import sqlalchemy as sa


revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("resource_capacity") as batch_op:
        batch_op.add_column(
            sa.Column("leveling_plans", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("leveling_plan_version", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade():
    with op.batch_alter_table("resource_capacity") as batch_op:
        batch_op.drop_column("leveling_plans")
        batch_op.drop_column("leveling_plan_version")
