import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


PATH = Path(__file__).parents[1] / "migrations" / "versions" / "0029_dashboard_widget_matrix.py"
SPEC = importlib.util.spec_from_file_location("dashboard_widget_matrix", PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_dashboard_matrix_migration_adds_nullable_secondary_dimension_and_downgrades():
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
        connection.execute(widgets.insert().values(id=1, name="Widget existente"))
        with Operations.context(MigrationContext.configure(connection, opts={"render_as_batch": True})):
            MIGRATION.upgrade()
        migrated = sa.Table("dashboard_widgets", sa.MetaData(), autoload_with=connection)
        assert migrated.c.group_by_secondary.nullable
        assert connection.scalar(sa.select(migrated.c.name).where(migrated.c.id == 1)) == "Widget existente"
        with Operations.context(MigrationContext.configure(connection, opts={"render_as_batch": True})):
            MIGRATION.downgrade()
        assert "group_by_secondary" not in {
            column["name"] for column in sa.inspect(connection).get_columns("dashboard_widgets")
        }
    engine.dispose()
