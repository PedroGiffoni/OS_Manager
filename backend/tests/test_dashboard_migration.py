import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


PATH = Path(__file__).parents[1] / "migrations" / "versions" / "0027_independent_dashboards.py"
SPEC = importlib.util.spec_from_file_location("independent_dashboards", PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def run(connection, operation):
    with Operations.context(MigrationContext.configure(connection, opts={"render_as_batch": True})):
        operation()


def test_dashboard_migration_preserves_widgets_in_owner_default_dashboard_and_downgrades():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    users = sa.Table("users", metadata, sa.Column("id", sa.Integer, primary_key=True))
    widgets = sa.Table(
        "dashboard_widgets",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(users.insert(), [{"id": 1}, {"id": 2}])
        connection.execute(widgets.insert().values(id=12, user_id=1, name="Status legado"))
        run(connection, MIGRATION.upgrade)
        dashboards = sa.Table("dashboards", sa.MetaData(), autoload_with=connection)
        migrated_widgets = sa.Table("dashboard_widgets", sa.MetaData(), autoload_with=connection)
        owner_dashboard = connection.execute(
            sa.select(dashboards.c.id).where(
                dashboards.c.user_id == 1, dashboards.c.is_default.is_(True)
            )
        ).scalar_one()
        assert connection.scalar(
            sa.select(migrated_widgets.c.dashboard_id).where(migrated_widgets.c.id == 12)
        ) == owner_dashboard
        assert connection.scalar(sa.select(sa.func.count()).select_from(dashboards)) == 2

        run(connection, MIGRATION.downgrade)
        assert "dashboard_id" not in {
            column["name"] for column in sa.inspect(connection).get_columns("dashboard_widgets")
        }
        assert "dashboards" not in sa.inspect(connection).get_table_names()
    engine.dispose()
