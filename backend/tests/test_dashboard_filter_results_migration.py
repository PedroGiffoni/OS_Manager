import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


PATH = Path(__file__).parents[1] / "migrations" / "versions" / "0035_dashboard_filter_results.py"
SPEC = importlib.util.spec_from_file_location("dashboard_filter_results", PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_filter_results_migration_backfills_existing_widgets_and_downgrades():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    widgets = sa.Table(
        "dashboard_widgets",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(widgets.insert().values(id=1, name="Widget anterior"))
        with Operations.context(MigrationContext.configure(connection, opts={"render_as_batch": True})):
            MIGRATION.upgrade()
        migrated = sa.Table("dashboard_widgets", sa.MetaData(), autoload_with=connection)
        assert connection.scalar(sa.select(migrated.c.result_columns).where(migrated.c.id == 1)) == [
            "key", "summary", "status", "priority", "assignee", "due"
        ]
        assert connection.scalar(sa.select(migrated.c.max_results).where(migrated.c.id == 1)) == 50
        with Operations.context(MigrationContext.configure(connection, opts={"render_as_batch": True})):
            MIGRATION.downgrade()
        assert {column["name"] for column in sa.inspect(connection).get_columns("dashboard_widgets")} == {
            "id", "name"
        }
    engine.dispose()
