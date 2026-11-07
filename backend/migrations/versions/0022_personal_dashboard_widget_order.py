"""Store dashboard widget order per viewer, including shared widgets."""

from alembic import op
import sqlalchemy as sa


revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dashboard_widget_positions",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("widget_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_dashboard_widget_position_nonnegative"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["widget_id"], ["dashboard_widgets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "widget_id"),
    )
    op.create_index(
        "ix_dashboard_widget_positions_user_position",
        "dashboard_widget_positions",
        ["user_id", "position"],
    )


def downgrade():
    op.drop_index(
        "ix_dashboard_widget_positions_user_position",
        table_name="dashboard_widget_positions",
    )
    op.drop_table("dashboard_widget_positions")
