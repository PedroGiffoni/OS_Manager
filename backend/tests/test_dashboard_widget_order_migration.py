import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "migrations"
    / "versions"
    / "0022_personal_dashboard_widget_order.py"
)
SPEC = importlib.util.spec_from_file_location("dashboard_widget_order_migration", MIGRATION_PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def run_migration(connection, operation):
    context = MigrationContext.configure(connection)
    with Operations.context(context):
        operation()


def test_dashboard_widget_order_migration_persists_per_viewer_and_cascades():
    engine = sa.create_engine("sqlite:///:memory:")

    @sa.event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    metadata = sa.MetaData()
    users = sa.Table("users", metadata, sa.Column("id", sa.Integer, primary_key=True))
    widgets = sa.Table(
        "dashboard_widgets", metadata, sa.Column("id", sa.Integer, primary_key=True)
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(users.insert(), [{"id": 1}, {"id": 2}])
        connection.execute(widgets.insert(), [{"id": 10}])
        run_migration(connection, MIGRATION.upgrade)
        positions = sa.Table(
            "dashboard_widget_positions", sa.MetaData(), autoload_with=connection
        )
        connection.execute(
            positions.insert(),
            [
                {"user_id": 1, "widget_id": 10, "position": 0},
                {"user_id": 2, "widget_id": 10, "position": 4},
            ],
        )
        assert connection.scalar(
            sa.select(positions.c.position).where(positions.c.user_id == 1)
        ) == 0
        assert connection.scalar(
            sa.select(positions.c.position).where(positions.c.user_id == 2)
        ) == 4
        with pytest.raises(sa.exc.IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    positions.insert().values(user_id=1, widget_id=10, position=-1)
                )

        connection.execute(widgets.delete().where(widgets.c.id == 10))
        assert connection.scalar(sa.select(sa.func.count()).select_from(positions)) == 0
        run_migration(connection, MIGRATION.downgrade)
        assert "dashboard_widget_positions" not in sa.inspect(connection).get_table_names()

    engine.dispose()
