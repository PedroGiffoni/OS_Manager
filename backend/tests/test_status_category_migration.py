import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


PATH = Path(__file__).parents[1] / "migrations" / "versions" / "0032_kanban_status_categories.py"
SPEC = importlib.util.spec_from_file_location("status_category_migration", PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_status_category_migration_backfills_order_and_is_reversible():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    columns = sa.Table(
        "kanban_columns",
        metadata,
        sa.Column("key", sa.String(60), primary_key=True),
        sa.Column("workflow_order", sa.Integer(), nullable=False),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            columns.insert(),
            [
                {"key": "backlog", "workflow_order": 0},
                {"key": "production", "workflow_order": 200},
                {"key": "review", "workflow_order": 300},
                {"key": "done", "workflow_order": 1000},
                {"key": "custom_1", "workflow_order": 250},
            ],
        )
        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.upgrade()
        values = dict(
            connection.execute(sa.text("SELECT key, category FROM kanban_columns")).all()
        )
        assert values == {
            "backlog": "todo",
            "production": "in_progress",
            "review": "in_progress",
            "done": "done",
            "custom_1": "in_progress",
        }
        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.downgrade()
        assert "category" not in {column["name"] for column in sa.inspect(connection).get_columns("kanban_columns")}
    engine.dispose()
