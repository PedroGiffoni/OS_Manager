"""Store per-work-type workflow restrictions without duplicate transition rows."""

from alembic import op
import sqlalchemy as sa


revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "workflow_transitions",
        sa.Column("type_rules", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade():
    op.drop_column("workflow_transitions", "type_rules")
