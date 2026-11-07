"""Add independent dashboard containers and move existing widgets into each owner's default."""

from alembic import op
import sqlalchemy as sa


revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dashboards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_dashboards_user_name"),
    )
    op.create_index("ix_dashboards_user_id", "dashboards", ["user_id"])
    op.add_column("dashboard_widgets", sa.Column("dashboard_id", sa.Integer(), nullable=True))

    bind = op.get_bind()
    dashboard_ids = {}
    for (user_id,) in bind.execute(sa.text("SELECT id FROM users ORDER BY id")):
        dashboard_id = bind.execute(
            sa.text(
                "INSERT INTO dashboards (user_id, name, is_default, created_at) "
                "VALUES (:user_id, :name, :is_default, :created_at) RETURNING id"
            ),
            {
                "user_id": user_id,
                "name": "Visão geral",
                "is_default": True,
                "created_at": "1970-01-01T00:00:00+00:00",
            },
        ).scalar_one()
        dashboard_ids[user_id] = dashboard_id

    for user_id, dashboard_id in dashboard_ids.items():
        bind.execute(
            sa.text("UPDATE dashboard_widgets SET dashboard_id = :dashboard_id WHERE user_id = :user_id"),
            {"dashboard_id": dashboard_id, "user_id": user_id},
        )

    with op.batch_alter_table("dashboard_widgets") as batch_op:
        batch_op.alter_column("dashboard_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            "fk_dashboard_widgets_dashboard_id_dashboards",
            "dashboards",
            ["dashboard_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_dashboard_widgets_dashboard_id", ["dashboard_id"])


def downgrade():
    with op.batch_alter_table("dashboard_widgets") as batch_op:
        batch_op.drop_index("ix_dashboard_widgets_dashboard_id")
        batch_op.drop_constraint("fk_dashboard_widgets_dashboard_id_dashboards", type_="foreignkey")
        batch_op.drop_column("dashboard_id")
    op.drop_index("ix_dashboards_user_id", table_name="dashboards")
    op.drop_table("dashboards")
