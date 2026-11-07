"""Add allowlisted conditions and actions to transition rules."""

from alembic import op
import sqlalchemy as sa


revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "workflow_transitions",
        sa.Column("conditions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "workflow_transitions",
        sa.Column("actions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )


def downgrade():
    op.drop_column("workflow_transitions", "actions")
    op.drop_column("workflow_transitions", "conditions")
