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
    / "0020_automation_action_sequences.py"
)
SPEC = importlib.util.spec_from_file_location("automation_action_migration", MIGRATION_PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def run_migration(connection, operation):
    context = MigrationContext.configure(connection)
    with Operations.context(context):
        operation()


def engine_with_legacy_rule():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    table = sa.Table(
        "automation_rules",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("config", sa.JSON, nullable=False),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(table.insert().values(
            id=1,
            action="add_label",
            config={"text": "Legado", "color": "#2B4EDA"},
        ))
    return engine


def test_migration_backfills_legacy_action_and_downgrades_without_loss():
    engine = engine_with_legacy_rule()
    with engine.begin() as connection:
        run_migration(connection, MIGRATION.upgrade)
        migrated = sa.Table("automation_rules", sa.MetaData(), autoload_with=connection)
        assert connection.scalar(sa.select(migrated.c.actions).where(migrated.c.id == 1)) == [
            {"action": "add_label", "config": {"text": "Legado", "color": "#2B4EDA"}}
        ]

        run_migration(connection, MIGRATION.downgrade)
        legacy = sa.Table("automation_rules", sa.MetaData(), autoload_with=connection)
        row = connection.execute(sa.select(legacy.c.action, legacy.c.config)).one()
        assert row.action == "add_label"
        assert row.config == {"text": "Legado", "color": "#2B4EDA"}
    engine.dispose()


def test_migration_refuses_lossy_downgrade_of_action_sequence():
    engine = engine_with_legacy_rule()
    with engine.begin() as connection:
        run_migration(connection, MIGRATION.upgrade)
        migrated = sa.Table("automation_rules", sa.MetaData(), autoload_with=connection)
        connection.execute(
            migrated.update()
            .where(migrated.c.id == 1)
            .values(actions=[
                {"action": "add_label", "config": {"text": "Um", "color": "#2B4EDA"}},
                {"action": "add_comment", "config": {"body": "Dois"}},
            ])
        )
        with pytest.raises(RuntimeError, match="múltiplas ações"):
            run_migration(connection, MIGRATION.downgrade)
        assert any(
            column["name"] == "actions"
            for column in sa.inspect(connection).get_columns("automation_rules")
        )
    engine.dispose()
