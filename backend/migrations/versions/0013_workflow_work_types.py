"""Allow transition rules to target selected card types."""

from alembic import op
import sqlalchemy as sa


revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "workflow_transitions",
        sa.Column("work_types", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade():
    op.drop_column("workflow_transitions", "work_types")
