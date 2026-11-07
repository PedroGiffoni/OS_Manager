import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


PATH = Path(__file__).parents[1] / "migrations" / "versions" / "0030_optional_email_notifications.py"
SPEC = importlib.util.spec_from_file_location("email_notification_migration", PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_email_notification_migration_adds_and_removes_preferences_and_outbox():
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
        connection.execute(users.insert().values(id=1))
        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.upgrade()
        inspector = sa.inspect(connection)
        assert {"notification_preferences", "email_outbox"} <= set(inspector.get_table_names())
        assert {"ix_email_outbox_due", "ix_email_outbox_next_attempt_at"} <= {
            index["name"] for index in inspector.get_indexes("email_outbox")
        }
        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.downgrade()
        assert "notification_preferences" not in sa.inspect(connection).get_table_names()
        assert "email_outbox" not in sa.inspect(connection).get_table_names()
    engine.dispose()
