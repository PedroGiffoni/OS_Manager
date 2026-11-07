"""Add work hierarchy, releases, components, dependencies, and capacity data."""

from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
        "tasks",
        table_args=(sa.CheckConstraint(
            "estimated_minutes >= 0 AND used_minutes >= 0",
            name="ck_task_hours_nonnegative",
        ),),
    ) as batch:
        batch.add_column(sa.Column("work_type", sa.String(length=30), nullable=False, server_default="task"))
        batch.add_column(sa.Column("parent_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_tasks_parent_id_tasks", "tasks", ["parent_id"], ["id"])
        batch.create_check_constraint("ck_task_not_own_parent", "parent_id IS NULL OR parent_id != id")
        batch.create_index("ix_tasks_parent_id", ["parent_id"])

    with op.batch_alter_table("kanban_saved_views") as batch:
        batch.add_column(sa.Column("shared", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        "releases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("starts", sa.String(), nullable=True),
        sa.Column("due", sa.String(), nullable=True),
        sa.Column("released_at", sa.String(), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_releases_archived", "releases", ["archived"])
    op.create_table(
        "components",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_components_active", "components", ["active"])
    op.create_table(
        "task_releases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("release_id", sa.Integer(), sa.ForeignKey("releases.id"), nullable=False),
        sa.Column("linked_at", sa.String(), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.UniqueConstraint("task_id", "release_id"),
    )
    op.create_index("ix_task_releases_task_id", "task_releases", ["task_id"])
    op.create_index("ix_task_releases_release_id", "task_releases", ["release_id"])
    op.create_table(
        "task_components",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("component_id", sa.Integer(), sa.ForeignKey("components.id"), nullable=False),
        sa.Column("linked_at", sa.String(), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.UniqueConstraint("task_id", "component_id"),
    )
    op.create_index("ix_task_components_task_id", "task_components", ["task_id"])
    op.create_index("ix_task_components_component_id", "task_components", ["component_id"])
    op.create_table(
        "task_dependencies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("target_task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("link_type", sa.String(length=20), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.UniqueConstraint("source_task_id", "target_task_id", "link_type"),
        sa.CheckConstraint("source_task_id != target_task_id", name="ck_dependency_not_self"),
        sa.CheckConstraint("link_type IN ('blocks', 'relates', 'duplicates')", name="ck_dependency_link_type"),
    )
    op.create_index("ix_task_dependencies_source_task_id", "task_dependencies", ["source_task_id"])
    op.create_index("ix_task_dependencies_target_task_id", "task_dependencies", ["target_task_id"])
    op.create_table(
        "resource_capacity",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("starts", sa.String(), nullable=False),
        sa.Column("ends", sa.String(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.CheckConstraint("(supplier_id IS NULL) != (user_id IS NULL)", name="ck_capacity_one_resource"),
        sa.CheckConstraint("minutes >= 0", name="ck_capacity_nonnegative"),
        sa.UniqueConstraint("supplier_id", "user_id", "starts", "ends"),
    )
    op.create_index("ix_resource_capacity_supplier_id", "resource_capacity", ["supplier_id"])
    op.create_index("ix_resource_capacity_user_id", "resource_capacity", ["user_id"])


def downgrade():
    op.drop_table("resource_capacity")
    op.drop_table("task_dependencies")
    op.drop_table("task_components")
    op.drop_table("task_releases")
    op.drop_table("components")
    op.drop_table("releases")
    with op.batch_alter_table("kanban_saved_views") as batch:
        batch.drop_column("shared")
    with op.batch_alter_table("tasks") as batch:
        batch.drop_index("ix_tasks_parent_id")
        batch.drop_constraint("ck_task_not_own_parent", type_="check")
        batch.drop_constraint("fk_tasks_parent_id_tasks", type_="foreignkey")
        batch.drop_column("parent_id")
        batch.drop_column("work_type")
        batch.drop_constraint("ck_task_hours_nonnegative", type_="check")
