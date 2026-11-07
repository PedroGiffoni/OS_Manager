"""Persist a safe advanced filter on each dashboard widget."""

from alembic import op
import sqlalchemy as sa


revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "dashboard_widgets",
        sa.Column("jql", sa.Text(), nullable=False, server_default=""),
    )


def downgrade():
    with op.batch_alter_table("dashboard_widgets") as batch_op:
        batch_op.drop_column("jql")
