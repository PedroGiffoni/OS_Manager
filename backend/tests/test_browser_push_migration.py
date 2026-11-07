import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


PATH = Path(__file__).parents[1] / "migrations" / "versions" / "0031_browser_push_notifications.py"
SPEC = importlib.util.spec_from_file_location("browser_push_migration", PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_push_migration_adds_encrypted_device_registry_and_outbox():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    users = sa.Table("users", metadata, sa.Column("id", sa.Integer, primary_key=True))
    sa.Table(
        "in_app_notifications",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey(users.c.id), nullable=False),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.upgrade()
        inspector = sa.inspect(connection)
        assert {"push_subscriptions", "push_outbox"} <= set(inspector.get_table_names())
        assert inspector.get_pk_constraint("push_subscriptions")["constrained_columns"] == [
            "endpoint_hash"
        ]
        assert {"ix_push_outbox_due", "ix_push_outbox_next_attempt_at"} <= {
            index["name"] for index in inspector.get_indexes("push_outbox")
        }
        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.downgrade()
        tables = set(sa.inspect(connection).get_table_names())
        assert "push_subscriptions" not in tables and "push_outbox" not in tables
    engine.dispose()
