"""Add a second grouping dimension for matrix dashboard gadgets."""

from alembic import op
import sqlalchemy as sa


revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("dashboard_widgets") as batch_op:
        batch_op.add_column(sa.Column("group_by_secondary", sa.String(length=30), nullable=True))


def downgrade():
    with op.batch_alter_table("dashboard_widgets") as batch_op:
        batch_op.drop_column("group_by_secondary")
