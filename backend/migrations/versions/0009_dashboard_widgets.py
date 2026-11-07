"""Add user configurable dashboard widgets."""

from alembic import op
import sqlalchemy as sa


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dashboard_widgets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("group_by", sa.String(length=30), nullable=False),
        sa.Column("measure", sa.String(length=30), nullable=False, server_default="count"),
        sa.Column("chart", sa.String(length=20), nullable=False, server_default="bar"),
        sa.Column("shared", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("user_id", "name"),
    )
    op.create_index("ix_dashboard_widgets_user_id", "dashboard_widgets", ["user_id"])


def downgrade():
    op.drop_table("dashboard_widgets")
