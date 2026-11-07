"""Add optional WIP limits to Kanban columns."""

from alembic import op
import sqlalchemy as sa


revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("kanban_columns") as batch_op:
        batch_op.add_column(sa.Column("wip_limit", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "ck_kanban_columns_wip_limit_positive",
            "wip_limit IS NULL OR wip_limit > 0",
        )


def downgrade():
    with op.batch_alter_table("kanban_columns") as batch_op:
        batch_op.drop_constraint("ck_kanban_columns_wip_limit_positive", type_="check")
        batch_op.drop_column("wip_limit")
