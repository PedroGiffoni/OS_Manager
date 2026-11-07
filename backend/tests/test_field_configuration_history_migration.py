import importlib.util
import json
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "migrations"
    / "versions"
    / "0021_searchable_field_configuration_history.py"
)
SPEC = importlib.util.spec_from_file_location("field_config_history_migration", MIGRATION_PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def run_migration(connection, operation):
    context = MigrationContext.configure(connection)
    with Operations.context(context):
        operation()


def test_migration_backfills_configuration_property_aliases_and_downgrades_cleanly():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    history = sa.Table(
        "task_field_changes",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("audit_id", sa.Integer, nullable=False),
        sa.Column("field", sa.String(80), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("before_json", sa.Text, nullable=False),
        sa.Column("after_json", sa.Text, nullable=False),
        sa.UniqueConstraint("audit_id", "field", "kind"),
    )
    metadata.create_all(engine)
    old = {"id": "area", "label": "Área", "type": "text", "required": False}
    new = {"id": "area", "label": "Área responsável", "type": "text", "required": True}
    with engine.begin() as connection:
        connection.execute(history.insert().values(
            audit_id=1,
            field="area",
            kind="configuration",
            before_json=json.dumps(old),
            after_json=json.dumps(new),
        ))
        connection.execute(history.insert().values(
            audit_id=2,
            field="new_field",
            kind="configuration",
            before_json="null",
            after_json=json.dumps({"id": "new_field", "label": "Novo campo", "type": "text"}),
        ))
        run_migration(connection, MIGRATION.upgrade)
        rows = connection.execute(
            sa.select(history.c.field, history.c.before_json, history.c.after_json)
            .where(history.c.audit_id == 1, history.c.kind == "configuration_property")
            .order_by(history.c.field)
        ).all()
        assert [(row.field, json.loads(row.before_json), json.loads(row.after_json)) for row in rows] == [
            ("config_area_label", "Área", "Área responsável"),
            ("config_area_required", False, True),
        ]
        added = connection.execute(
            sa.select(history.c.field, history.c.before_json, history.c.after_json)
            .where(history.c.audit_id == 2, history.c.kind == "configuration_property")
            .order_by(history.c.field)
        ).all()
        assert [(row.field, json.loads(row.before_json), json.loads(row.after_json)) for row in added] == [
            ("config_new_field_id", None, "new_field"),
            ("config_new_field_label", None, "Novo campo"),
            ("config_new_field_type", None, "text"),
        ]
        run_migration(connection, MIGRATION.downgrade)
        remaining = connection.execute(sa.select(history.c.field, history.c.kind)).all()
        assert remaining == [("area", "configuration"), ("new_field", "configuration")]
    engine.dispose()
