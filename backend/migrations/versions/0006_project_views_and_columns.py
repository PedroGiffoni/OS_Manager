"""Add saved board views, extensible workflow columns, and planned task starts."""

from alembic import op
import sqlalchemy as sa


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("planned_start", sa.String(), nullable=True))
        batch.add_column(sa.Column("board_origin_status", sa.String(), nullable=True))

    op.create_table(
        "kanban_columns",
        sa.Column("key", sa.String(length=60), primary_key=True),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("workflow_order", sa.Integer(), nullable=False),
        sa.Column("view_order", sa.Integer(), nullable=False),
        sa.UniqueConstraint("workflow_order"),
        sa.UniqueConstraint("view_order"),
    )
    columns = sa.table(
        "kanban_columns",
        sa.column("key", sa.String),
        sa.column("title", sa.String),
        sa.column("is_system", sa.Boolean),
        sa.column("workflow_order", sa.Integer),
        sa.column("view_order", sa.Integer),
    )
    op.bulk_insert(
        columns,
        [
            {"key": "backlog", "title": "Backlog", "is_system": True, "workflow_order": 0, "view_order": 0},
            {"key": "todo", "title": "A fazer", "is_system": True, "workflow_order": 100, "view_order": 1},
            {"key": "production", "title": "Em produção", "is_system": True, "workflow_order": 200, "view_order": 2},
            {"key": "review", "title": "Em revisão", "is_system": True, "workflow_order": 300, "view_order": 3},
            {"key": "done", "title": "Concluído", "is_system": True, "workflow_order": 1000, "view_order": 4},
        ],
    )
    op.create_table(
        "kanban_saved_views",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("layout", sa.String(length=20), nullable=False, server_default="board"),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("user_id", "name"),
    )
    op.create_index("ix_kanban_saved_views_user_id", "kanban_saved_views", ["user_id"])


def downgrade():
    op.drop_index("ix_kanban_saved_views_user_id", table_name="kanban_saved_views")
    op.drop_table("kanban_saved_views")
    op.drop_table("kanban_columns")
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("board_origin_status")
        batch.drop_column("planned_start")
