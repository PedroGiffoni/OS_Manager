from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.main import list_automation_runs


def test_automation_run_log_is_paginated_authorized_and_redacted():
    audit = SimpleNamespace(
        id=91,
        created_at="2026-11-07T12:00:00+00:00",
        details={
            "rule_id": 7,
            "rule_name": "Auditoria da regra",
            "trigger": "card_created",
            "actor_name": "gestor",
            "changes": {"priority": {"before": 0, "after": 5}},
            "comment_ids": [12],
            "watcher_ids_added": [],
            "skipped_actions": [],
            "secret_comment": "texto confidencial que não deve aparecer no log",
        },
    )
    task = SimpleNamespace(id=33, title="Card da auditoria")

    class Database:
        def execute(self, query):
            assert query is not None
            return SimpleNamespace(all=lambda: [(audit, task)])

    admin = SimpleNamespace(role="admin", grants=[])
    entry = list_automation_runs(limit=1, offset=0, user=admin, db=Database())[0]
    assert entry["rule_name"] == "Auditoria da regra"
    assert entry["task_key"] == "OS-33"
    assert entry["task_title"] == "Card da auditoria"
    assert entry["changed_fields"] == ["priority"]
    assert entry["comments_added"] == 1
    assert "secret_comment" not in entry
    assert "texto confidencial" not in str(entry)
    assert "cost" not in str(entry).lower()

    with pytest.raises(HTTPException) as supplier_denied:
        list_automation_runs(limit=50, offset=0, user=SimpleNamespace(role="supplier", grants=[]), db=Database())
    assert supplier_denied.value.status_code == 403
    with pytest.raises(HTTPException) as manager_denied:
        list_automation_runs(limit=50, offset=0, user=SimpleNamespace(role="manager", grants=[]), db=Database())
    assert manager_denied.value.status_code == 403
    with pytest.raises(HTTPException) as invalid_pagination:
        list_automation_runs(limit=0, offset=0, user=admin, db=Database())
    assert invalid_pagination.value.status_code == 422
