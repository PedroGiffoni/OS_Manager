import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


PATH = Path(__file__).parents[1] / "migrations" / "versions" / "0026_worklog_comments.py"
SPEC = importlib.util.spec_from_file_location("worklog_comments", PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def run(connection, operation):
    with Operations.context(MigrationContext.configure(connection, opts={"render_as_batch": True})):
        operation()


def test_worklog_comment_migration_preserves_existing_hour_versions_and_downgrades():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    hours = sa.Table(
        "task_hours",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("task_id", sa.Integer, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(hours.insert().values(id=1, task_id=7, version=1))
        run(connection, MIGRATION.upgrade)
        migrated = sa.Table("task_hours", sa.MetaData(), autoload_with=connection)
        assert connection.scalar(sa.select(migrated.c.comment).where(migrated.c.id == 1)) is None
        connection.execute(migrated.update().where(migrated.c.id == 1).values(comment="Versão inicial"))
        assert connection.scalar(sa.select(migrated.c.comment).where(migrated.c.id == 1)) == "Versão inicial"
        run(connection, MIGRATION.downgrade)
        assert "comment" not in {column["name"] for column in sa.inspect(connection).get_columns("task_hours")}
    engine.dispose()
