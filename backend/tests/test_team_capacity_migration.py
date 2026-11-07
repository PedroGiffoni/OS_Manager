import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest


PATH = Path(__file__).parents[1] / "migrations" / "versions" / "0028_team_capacity.py"
SPEC = importlib.util.spec_from_file_location("team_capacity", PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def run(connection, operation):
    with Operations.context(MigrationContext.configure(connection, opts={"render_as_batch": True})):
        operation()


def test_team_capacity_migration_preserves_resource_rows_and_rolls_back_schema():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    users = sa.Table("users", metadata, sa.Column("id", sa.Integer, primary_key=True))
    sa.Table("suppliers", metadata, sa.Column("id", sa.Integer, primary_key=True))
    groups = sa.Table("user_groups", metadata, sa.Column("id", sa.Integer, primary_key=True))
    capacity = sa.Table(
        "resource_capacity",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("supplier_id", sa.Integer, nullable=True),
        sa.Column("user_id", sa.Integer, nullable=True),
        sa.Column("starts", sa.String, nullable=False),
        sa.Column("ends", sa.String, nullable=False),
        sa.Column("minutes", sa.Integer, nullable=False),
        sa.Column("notes", sa.Text, nullable=False),
        sa.Column("author_id", sa.Integer, nullable=False),
        sa.CheckConstraint(
            "(supplier_id IS NULL) != (user_id IS NULL)", name="ck_capacity_one_resource"
        ),
        sa.CheckConstraint("minutes >= 0", name="ck_capacity_nonnegative"),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(users.insert().values(id=1))
        connection.execute(groups.insert().values(id=9))
        connection.execute(
            capacity.insert().values(
                id=3,
                user_id=1,
                supplier_id=None,
                starts="2026-11-01",
                ends="2026-11-30",
                minutes=2400,
                notes="Legado",
                author_id=1,
            )
        )
        run(connection, MIGRATION.upgrade)
        upgraded = sa.Table("resource_capacity", sa.MetaData(), autoload_with=connection)
        assert connection.scalar(
            sa.select(upgraded.c.minutes).where(upgraded.c.id == 3)
        ) == 2400
        connection.execute(
            upgraded.insert().values(
                id=4,
                user_id=None,
                supplier_id=None,
                group_id=9,
                group_member_ids="[1]",
                starts="2026-12-01",
                ends="2026-12-31",
                minutes=4800,
                notes="Equipe",
                author_id=1,
            )
        )
        assert connection.scalar(
            sa.select(upgraded.c.group_member_ids).where(upgraded.c.id == 4)
        ) == "[1]"

        with pytest.raises(RuntimeError, match="capacidade de equipe"):
            run(connection, MIGRATION.downgrade)
        connection.execute(upgraded.delete().where(upgraded.c.id == 4))
        run(connection, MIGRATION.downgrade)
        downgraded = sa.Table("resource_capacity", sa.MetaData(), autoload_with=connection)
        assert "group_id" not in downgraded.c
        assert connection.scalar(
            sa.select(downgraded.c.minutes).where(downgraded.c.id == 3)
        ) == 2400
    engine.dispose()
