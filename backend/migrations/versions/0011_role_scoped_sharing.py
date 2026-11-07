"""Allow saved views and dashboard widgets to be shared by internal roles."""

from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("kanban_saved_views") as batch:
        batch.add_column(sa.Column("shared_roles", sa.JSON(), nullable=False, server_default="[]"))
    with op.batch_alter_table("dashboard_widgets") as batch:
        batch.add_column(sa.Column("shared_roles", sa.JSON(), nullable=False, server_default="[]"))
    bind = op.get_bind()
    legacy_roles = ["admin", "manager", "internal"]
    for table_name in ("kanban_saved_views", "dashboard_widgets"):
        table = sa.table(
            table_name,
            sa.column("shared", sa.Boolean()),
            sa.column("shared_roles", sa.JSON()),
        )
        bind.execute(
            sa.update(table)
            .where(table.c.shared.is_(True))
            .values(shared_roles=legacy_roles)
        )


def downgrade():
    with op.batch_alter_table("dashboard_widgets") as batch:
        batch.drop_column("shared_roles")
    with op.batch_alter_table("kanban_saved_views") as batch:
        batch.drop_column("shared_roles")
