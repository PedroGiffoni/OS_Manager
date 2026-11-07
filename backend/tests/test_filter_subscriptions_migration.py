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
    / "0023_scheduled_filter_subscriptions.py"
)
SPEC = importlib.util.spec_from_file_location("scheduled_filter_subscriptions", MIGRATION_PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def run_migration(connection, operation):
    context = MigrationContext.configure(connection, opts={"render_as_batch": True})
    with Operations.context(context):
        operation()


def test_subscription_migration_defaults_existing_alerts_and_cascades_matches():
    engine = sa.create_engine("sqlite:///:memory:")

    @sa.event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    metadata = sa.MetaData()
    users = sa.Table("users", metadata, sa.Column("id", sa.Integer, primary_key=True))
    tasks = sa.Table("tasks", metadata, sa.Column("id", sa.Integer, primary_key=True))
    notifications = sa.Table(
        "in_app_notifications",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.Integer, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.Integer, nullable=True),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("created_at", sa.String, nullable=False),
        sa.Column("read_at", sa.String, nullable=True),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(users.insert().values(id=1))
        connection.execute(tasks.insert().values(id=5))
        connection.execute(
            notifications.insert().values(
                id=9,
                user_id=1,
                task_id=5,
                action="task_updated",
                created_at="2026-11-07T12:00:00+00:00",
            )
        )
        run_migration(connection, MIGRATION.upgrade)
        notification_table = sa.Table(
            "in_app_notifications", sa.MetaData(), autoload_with=connection
        )
        assert connection.scalar(
            sa.select(notification_table.c.source_label).where(notification_table.c.id == 9)
        ) == ""
        subscriptions = sa.Table(
            "filter_subscriptions", sa.MetaData(), autoload_with=connection
        )
        connection.execute(
            subscriptions.insert().values(
                id=2,
                user_id=1,
                name="Revisão",
                query='status = "review"',
                frequency="daily",
                active=True,
                next_run_at="2026-11-08T12:00:00+00:00",
                last_error="",
                created_at="2026-11-07T12:00:00+00:00",
            )
        )
        matches = sa.Table(
            "filter_subscription_matches", sa.MetaData(), autoload_with=connection
        )
        connection.execute(
            matches.insert().values(subscription_id=2, task_id=5, matched_at="2026-11-07")
        )
        with pytest.raises(sa.exc.IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    subscriptions.insert().values(
                        id=3,
                        user_id=1,
                        name="Inválida",
                        query="x",
                        frequency="hourly",
                        active=True,
                        next_run_at="2026-11-08",
                        last_error="",
                        created_at="2026-11-07",
                    )
                )

        connection.execute(tasks.delete().where(tasks.c.id == 5))
        assert connection.scalar(sa.select(sa.func.count()).select_from(matches)) == 0
        run_migration(connection, MIGRATION.downgrade)
        assert "filter_subscription_matches" not in sa.inspect(connection).get_table_names()
        assert "filter_subscriptions" not in sa.inspect(connection).get_table_names()
        assert "source_label" not in {
            column["name"] for column in sa.inspect(connection).get_columns("in_app_notifications")
        }

    engine.dispose()
