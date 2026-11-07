import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


PATH = Path(__file__).parents[1] / "migrations" / "versions" / "0036_personal_calendar_feeds.py"
SPEC = importlib.util.spec_from_file_location("personal_calendar_feeds", PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_personal_calendar_feed_migration_adds_token_table_and_downgrades():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table("users", metadata, sa.Column("id", sa.Integer, primary_key=True))
    metadata.create_all(engine)
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection, opts={"render_as_batch": True})):
            MIGRATION.upgrade()
        table = sa.Table("calendar_feed_tokens", sa.MetaData(), autoload_with=connection)
        assert {column.name for column in table.columns} == {"user_id", "token_hash", "created_at"}
        assert sa.inspect(connection).get_pk_constraint("calendar_feed_tokens")["constrained_columns"] == ["user_id"]
        assert any(
            constraint["referred_table"] == "users" and constraint["options"].get("ondelete") == "CASCADE"
            for constraint in sa.inspect(connection).get_foreign_keys("calendar_feed_tokens")
        )
        with Operations.context(MigrationContext.configure(connection, opts={"render_as_batch": True})):
            MIGRATION.downgrade()
        assert "calendar_feed_tokens" not in sa.inspect(connection).get_table_names()
    engine.dispose()
