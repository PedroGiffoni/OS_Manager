import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


PATH = Path(__file__).parents[1] / "migrations" / "versions" / "0024_development_event_details.py"
SPEC = importlib.util.spec_from_file_location("development_event_details", PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def run(connection, operation):
    with Operations.context(MigrationContext.configure(connection, opts={"render_as_batch": True})):
        operation()


def test_metadata_migration_backfills_existing_events_and_downgrades():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    events = sa.Table(
        "development_events",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("provider", sa.String(20), nullable=False),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(events.insert().values(id=1, provider="github"))
        run(connection, MIGRATION.upgrade)
        migrated = sa.Table("development_events", sa.MetaData(), autoload_with=connection)
        assert connection.scalar(sa.select(migrated.c.metadata).where(migrated.c.id == 1)) == {}
        run(connection, MIGRATION.downgrade)
        assert "metadata" not in {column["name"] for column in sa.inspect(connection).get_columns("development_events")}
    engine.dispose()
