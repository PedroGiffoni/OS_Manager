"""Add internal groups and group-scoped sharing for saved views and widgets."""

from alembic import op
import sqlalchemy as sa


revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "user_group_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "group_id",
            sa.Integer(),
            sa.ForeignKey("user_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.UniqueConstraint("group_id", "user_id"),
    )
    op.create_index("ix_user_group_memberships_group_id", "user_group_memberships", ["group_id"])
    op.create_index("ix_user_group_memberships_user_id", "user_group_memberships", ["user_id"])
    op.add_column(
        "kanban_saved_views",
        sa.Column("shared_group_ids", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "dashboard_widgets",
        sa.Column("shared_group_ids", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade():
    op.drop_column("dashboard_widgets", "shared_group_ids")
    op.drop_column("kanban_saved_views", "shared_group_ids")
    op.drop_index("ix_user_group_memberships_user_id", table_name="user_group_memberships")
    op.drop_index("ix_user_group_memberships_group_id", table_name="user_group_memberships")
    op.drop_table("user_group_memberships")
    op.drop_table("user_groups")
