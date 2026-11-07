"""Configure columns and row limit for dashboard filter-results widgets."""

from alembic import op
import sqlalchemy as sa


revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("dashboard_widgets") as batch_op:
        batch_op.add_column(
            sa.Column(
                "result_columns",
                sa.JSON(),
                nullable=False,
                server_default='["key","summary","status","priority","assignee","due"]',
            )
        )
        batch_op.add_column(
            sa.Column("max_results", sa.Integer(), nullable=False, server_default="50")
        )


def downgrade():
    with op.batch_alter_table("dashboard_widgets") as batch_op:
        batch_op.drop_column("max_results")
        batch_op.drop_column("result_columns")
