"""Give Kanban columns explicit Jira-style status categories."""

from alembic import op
import sqlalchemy as sa


revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("kanban_columns", sa.Column("category", sa.String(length=20), nullable=True))
    table = sa.table(
        "kanban_columns",
        sa.column("key", sa.String(length=60)),
        sa.column("workflow_order", sa.Integer()),
        sa.column("category", sa.String(length=20)),
    )
    production_order = sa.select(table.c.workflow_order).where(table.c.key == "production").scalar_subquery()
    boundary = sa.func.coalesce(production_order, 200)
    op.get_bind().execute(
        sa.update(table).values(
            category=sa.case(
                (table.c.key == "done", "done"),
                (table.c.workflow_order < boundary, "todo"),
                else_="in_progress",
            )
        )
    )
    with op.batch_alter_table("kanban_columns") as batch_op:
        batch_op.alter_column(
            "category",
            existing_type=sa.String(length=20),
            nullable=False,
            server_default="todo",
        )
        batch_op.create_check_constraint(
            "ck_kanban_columns_category",
            "category IN ('todo', 'in_progress', 'done')",
        )


def downgrade():
    with op.batch_alter_table("kanban_columns") as batch_op:
        batch_op.drop_constraint("ck_kanban_columns_category", type_="check")
        batch_op.drop_column("category")
