"""Persist user-defined colored labels on each task."""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "tasks",
        sa.Column("labels", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )


def downgrade():
    op.drop_column("tasks", "labels")
