"""Store an immutable comment with each submitted hours version."""

from alembic import op
import sqlalchemy as sa


revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("task_hours", sa.Column("comment", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("task_hours") as batch_op:
        batch_op.drop_column("comment")
