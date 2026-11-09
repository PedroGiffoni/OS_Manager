"""Introduce isolated boards and explicit membership access."""

from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa


revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


SCOPED_TABLES = (
    "tasks", "sprints", "audit_logs", "kanban_saved_views", "saved_filters",
    "in_app_notifications", "filter_subscriptions", "releases", "components",
    "resource_capacity", "workflow_transitions", "automation_rules",
    "dashboard_widgets", "dashboards", "development_events",
)
BOARD_UNIQUES = {
    "kanban_saved_views": (("user_id", "name"), ("board_id", "user_id", "name")),
    "saved_filters": (("owner_id", "name"), ("board_id", "owner_id", "name")),
    "filter_subscriptions": (("user_id", "name"), ("board_id", "user_id", "name")),
    "releases": (("name",), ("board_id", "name")),
    "components": (("name",), ("board_id", "name")),
    "resource_capacity": (("supplier_id", "user_id", "starts", "ends"), ("board_id", "supplier_id", "user_id", "starts", "ends")),
    "workflow_transitions": (("source", "target"), ("board_id", "source", "target")),
    "dashboard_widgets": (("user_id", "name"), ("board_id", "user_id", "name")),
    "dashboards": (("user_id", "name"), ("board_id", "user_id", "name")),
}


def upgrade():
    op.create_table(
        "boards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_index("ix_boards_active", "boards", ["active"])
    op.create_table(
        "board_members",
        sa.Column("board_id", sa.Integer(), sa.ForeignKey("boards.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("granted_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_index("ix_board_members_user_id", "board_members", ["user_id"])

    bind = op.get_bind()
    author_id = bind.execute(sa.text("SELECT MIN(id) FROM users")).scalar()
    stamp = datetime.now(timezone.utc).isoformat()
    bind.execute(
        sa.text("INSERT INTO boards (id, name, description, active, author_id, created_at) VALUES (1, :name, :description, :active, :author_id, :created_at)"),
        {"name": "Quadro principal", "description": "Quadro criado para preservar os dados anteriores à separação por quadros.", "active": True, "author_id": author_id, "created_at": stamp},
    )
    if bind.dialect.name == "postgresql":
        bind.execute(sa.text("SELECT setval(pg_get_serial_sequence('boards', 'id'), (SELECT MAX(id) FROM boards))"))
    if author_id is not None:
        bind.execute(
            sa.text("INSERT INTO board_members (board_id, user_id, granted_by, created_at) SELECT 1, id, :author_id, :created_at FROM users"),
            {"author_id": author_id, "created_at": stamp},
        )

    for table in SCOPED_TABLES:
        table_args = ()
        if table == "sprints":
            table_args = (sa.CheckConstraint("ends >= starts"),)
        elif table == "tasks":
            table_args = (sa.CheckConstraint("estimated_minutes >= 0 AND used_minutes >= 0"),)
        with op.batch_alter_table(table, recreate="always" if bind.dialect.name == "sqlite" else "auto", table_args=table_args) as batch:
            batch.add_column(sa.Column("board_id", sa.Integer(), sa.ForeignKey("boards.id", name=f"fk_{table}_board_id_boards"), nullable=False, server_default="1"))
        op.create_index(f"ix_{table}_board_id", table, ["board_id"])

    # Replace global uniqueness rules with per-board uniqueness without discarding rows.
    convention = {"uq": "uq_%(table_name)s_%(column_0_N_name)s"}
    inspector = sa.inspect(bind)
    for table, (old_columns, new_columns) in BOARD_UNIQUES.items():
        candidates = [
            item for item in inspector.get_unique_constraints(table)
            if tuple(item.get("column_names") or ()) == old_columns
        ]
        if not candidates:
            raise RuntimeError(f"Unique constraint not found for {table}: {old_columns}")
        old_name = candidates[0].get("name")
        if old_name is None:
            old_name = f"uq_{table}_{'_'.join(old_columns)}"
        with op.batch_alter_table(
            table,
            recreate="always" if bind.dialect.name == "sqlite" else "auto",
            naming_convention=convention,
        ) as batch:
            batch.drop_constraint(old_name, type_="unique")
            batch.create_unique_constraint(f"uq_{table}_board_scope", new_columns)

    # Columns use board-scoped status keys: the same workflow keys can safely exist in each board.
    op.create_table(
        "kanban_columns_new",
        sa.Column("key", sa.String(60), nullable=False),
        sa.Column("board_id", sa.Integer(), sa.ForeignKey("boards.id"), nullable=False, server_default="1"),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("workflow_order", sa.Integer(), nullable=False),
        sa.Column("view_order", sa.Integer(), nullable=False),
        sa.Column("wip_limit", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("key", "board_id"),
        sa.UniqueConstraint("board_id", "workflow_order"),
        sa.UniqueConstraint("board_id", "view_order"),
        sa.CheckConstraint("category IN ('todo', 'in_progress', 'done')", name="ck_kanban_columns_category"),
        sa.CheckConstraint("wip_limit IS NULL OR wip_limit > 0", name="ck_kanban_columns_wip_limit_positive"),
    )
    bind.execute(sa.text("INSERT INTO kanban_columns_new (key, board_id, title, is_system, category, workflow_order, view_order, wip_limit) SELECT key, 1, title, is_system, category, workflow_order, view_order, wip_limit FROM kanban_columns"))
    op.drop_table("kanban_columns")
    op.rename_table("kanban_columns_new", "kanban_columns")
    op.create_index("ix_kanban_columns_board_id", "kanban_columns", ["board_id"])


def downgrade():
    bind = op.get_bind()
    board_count = bind.execute(sa.text("SELECT COUNT(*) FROM boards")).scalar_one()
    if board_count > 1:
        raise RuntimeError(
            "Cannot downgrade multiple boards without losing board-specific workflow data. "
            "Export and reconcile those boards before returning to a single-board schema."
        )
    inspector = sa.inspect(bind)
    convention = {"uq": "uq_%(table_name)s_%(column_0_N_name)s"}
    for table, (old_columns, new_columns) in reversed(list(BOARD_UNIQUES.items())):
        current = [
            item for item in inspector.get_unique_constraints(table)
            if tuple(item.get("column_names") or ()) == new_columns
        ]
        if not current:
            raise RuntimeError(f"Board-scoped unique constraint not found for {table}.")
        new_name = current[0].get("name") or f"uq_{table}_{'_'.join(new_columns)}"
        with op.batch_alter_table(
            table,
            recreate="always" if bind.dialect.name == "sqlite" else "auto",
            naming_convention=convention,
        ) as batch:
            batch.drop_constraint(new_name, type_="unique")
            batch.create_unique_constraint(f"uq_{table}_legacy", old_columns)
    op.rename_table("kanban_columns", "kanban_columns_scoped")
    op.create_table(
        "kanban_columns",
        sa.Column("key", sa.String(60), primary_key=True),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("workflow_order", sa.Integer(), nullable=False, unique=True),
        sa.Column("view_order", sa.Integer(), nullable=False, unique=True),
        sa.Column("wip_limit", sa.Integer(), nullable=True),
        sa.CheckConstraint("category IN ('todo', 'in_progress', 'done')", name="ck_kanban_columns_category"),
        sa.CheckConstraint("wip_limit IS NULL OR wip_limit > 0", name="ck_kanban_columns_wip_limit_positive"),
    )
    # A downgrade retains the principal board's workflow columns only.
    op.execute("INSERT INTO kanban_columns (key, title, is_system, category, workflow_order, view_order, wip_limit) SELECT key, title, is_system, category, workflow_order, view_order, wip_limit FROM kanban_columns_scoped WHERE board_id = 1")
    op.drop_table("kanban_columns_scoped")
    for table in reversed(SCOPED_TABLES):
        op.drop_index(f"ix_{table}_board_id", table_name=table)
        with op.batch_alter_table(
            table,
            recreate="always" if bind.dialect.name == "sqlite" else "auto",
        ) as batch:
            batch.drop_column("board_id")
    op.drop_index("ix_board_members_user_id", table_name="board_members")
    op.drop_table("board_members")
    op.drop_index("ix_boards_active", table_name="boards")
    op.drop_table("boards")
