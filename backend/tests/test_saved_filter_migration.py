import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


PATH = Path(__file__).parents[1] / "migrations" / "versions" / "0038_saved_shared_filters.py"
SPEC = importlib.util.spec_from_file_location("saved_shared_filters", PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_saved_filter_migration_adds_portable_table_and_downgrades():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table("users", metadata, sa.Column("id", sa.Integer, primary_key=True))
    metadata.create_all(engine)
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection, opts={"render_as_batch": True})):
            MIGRATION.upgrade()
        filters = sa.Table("saved_filters", sa.MetaData(), autoload_with=connection)
        assert {column.name for column in filters.columns} == {
            "id", "owner_id", "name", "query", "shared", "shared_roles",
            "shared_group_ids", "created_at", "updated_at",
        }
        assert any(
            foreign_key["referred_table"] == "users"
            and foreign_key["options"].get("ondelete") == "CASCADE"
            for foreign_key in sa.inspect(connection).get_foreign_keys("saved_filters")
        )
        with Operations.context(MigrationContext.configure(connection, opts={"render_as_batch": True})):
            MIGRATION.downgrade()
        assert "saved_filters" not in sa.inspect(connection).get_table_names()
    engine.dispose()
