import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


PATH = Path(__file__).parents[1] / "migrations" / "versions" / "0025_dashboard_widget_query.py"
SPEC = importlib.util.spec_from_file_location("dashboard_widget_query", PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def run(connection, operation):
    with Operations.context(MigrationContext.configure(connection, opts={"render_as_batch": True})):
        operation()


def test_dashboard_widget_query_migration_defaults_existing_widgets_and_downgrades():
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
        connection.execute(widgets.insert().values(id=1, name="Legado"))
        run(connection, MIGRATION.upgrade)
        migrated = sa.Table("dashboard_widgets", sa.MetaData(), autoload_with=connection)
        assert connection.scalar(sa.select(migrated.c.jql).where(migrated.c.id == 1)) == ""
        run(connection, MIGRATION.downgrade)
        assert "jql" not in {column["name"] for column in sa.inspect(connection).get_columns("dashboard_widgets")}
    engine.dispose()
