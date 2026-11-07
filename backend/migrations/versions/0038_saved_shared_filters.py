"""Add reusable personal and shared JQL filters."""

from alembic import op
import sqlalchemy as sa


revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "saved_filters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("shared", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("shared_roles", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("shared_group_ids", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "name", name="uq_saved_filters_owner_name"),
    )
    op.create_index("ix_saved_filters_owner_id", "saved_filters", ["owner_id"])
    op.create_index("ix_saved_filters_shared", "saved_filters", ["shared"])


def downgrade():
    op.drop_index("ix_saved_filters_shared", table_name="saved_filters")
    op.drop_index("ix_saved_filters_owner_id", table_name="saved_filters")
    op.drop_table("saved_filters")
