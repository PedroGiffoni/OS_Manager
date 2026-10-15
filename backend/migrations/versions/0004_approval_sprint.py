"""Attribute cost to the approval sprint without changing historical values."""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("hour_approvals") as batch:
        batch.add_column(sa.Column("sprint_id", sa.Integer(), nullable=True))
        batch.create_index("ix_hour_approvals_sprint_id", ["sprint_id"], unique=False)
        batch.create_foreign_key("fk_hour_approvals_sprint_id", "sprints", ["sprint_id"], ["id"])


def downgrade():
    with op.batch_alter_table("hour_approvals") as batch:
        batch.drop_constraint("fk_hour_approvals_sprint_id", type_="foreignkey")
        batch.drop_index("ix_hour_approvals_sprint_id")
        batch.drop_column("sprint_id")
