import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


PATH = Path(__file__).parents[1] / "migrations" / "versions" / "0037_weekly_automation_schedules.py"
SPEC = importlib.util.spec_from_file_location("weekly_automation_schedules", PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_weekly_schedule_migration_defaults_existing_rules_and_disables_on_downgrade():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    rules = sa.Table(
        "automation_rules",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("trigger", sa.String(40), nullable=False),
        sa.Column("schedule_time", sa.String(5)),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(rules.insert().values(id=1, trigger="scheduled_daily", schedule_time="08:30", enabled=True))
        with Operations.context(MigrationContext.configure(connection, opts={"render_as_batch": True})):
            MIGRATION.upgrade()
        migrated = sa.Table("automation_rules", sa.MetaData(), autoload_with=connection)
        assert connection.scalar(sa.select(migrated.c.schedule_frequency).where(migrated.c.id == 1)) == "daily"
        assert connection.scalar(sa.select(migrated.c.schedule_weekdays).where(migrated.c.id == 1)) == []
        connection.execute(
            migrated.update().where(migrated.c.id == 1).values(schedule_frequency="weekly", schedule_weekdays=[0, 2])
        )
        with Operations.context(MigrationContext.configure(connection, opts={"render_as_batch": True})):
            MIGRATION.downgrade()
        rolled_back = sa.Table("automation_rules", sa.MetaData(), autoload_with=connection)
        assert connection.scalar(sa.select(rolled_back.c.enabled).where(rolled_back.c.id == 1)) is False
        assert "schedule_frequency" not in rolled_back.c
        assert "schedule_weekdays" not in rolled_back.c
    engine.dispose()
