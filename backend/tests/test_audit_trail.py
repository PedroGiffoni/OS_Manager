from .test_acceptance import P, create, review, hours
from .test_report_filters import schema
from app.audit_trail import visible_details
from types import SimpleNamespace


def test_audit_custom_field_changes_keep_schema_visibility_when_field_is_removed():
    details = {"changes": [{
        "field": "restricted", "before": "private before", "after": "private after",
        "visible_to": ["admin"],
    }]}
    visible = visible_details(details, SimpleNamespace(role="supplier"), False, {})
    assert visible["changes"] == []
    admin = visible_details(details, SimpleNamespace(role="admin"), True, {})
    assert admin["changes"] == [{
        "field": "restricted", "before": "private before", "after": "private after",
    }]


def history(clients, task, user="admin"):
    response = clients[user].get(f"{P}/audit?entity=task&identity={task['id']}")
    assert response.status_code == 200, response.text
    return response.json()


def test_hours_audit_preserves_each_revision_and_actor(clients):
    task = review(clients)
    task = hours(clients, task, 600, 720).json()
    task = hours(clients, task, 600, 600).json()
    logs = [entry for entry in history(clients, task) if entry["action"] == "hours_submitted"]
    assert len(logs) == 4
    assert logs[0]["details"]["operation"] == "filled"
    assert logs[-1]["details"]["operation"] == "edited"
    assert logs[-2]["details"]["used_minutes"] == 720
    assert logs[-1]["details"]["used_minutes"] == 600
    assert logs[-1]["details"]["changes"] == [
        {"field": "used_minutes", "before": 720, "after": 600}
    ]
    assert logs[-1]["actor_name"] == "supplier" and logs[-1]["actor_id"] == 4
    assert all(
        entry["created_at"] and entry["details"]["hours_version"] == index + 1
        for index, entry in enumerate(logs)
    )
    assert logs[-1]["details"]["previous_hours_version"] == 3
    count = len(history(clients, task))
    failed = clients["supplier"].put(
        f"{P}/tasks/{task['id']}/hours",
        json={"version": 1, "estimated_minutes": 600, "used_minutes": 300},
    )
    assert failed.status_code == 409
    assert len(history(clients, task)) == count
    assert (
        clients["supplier"].get(f"{P}/audit?entity=task&identity={task['id']}").status_code == 403
    )
    assert (
        clients["admin"].delete(f"{P}/audit?entity=task&identity={task['id']}").status_code == 405
    )


def test_card_schema_values_and_comments_are_audited_without_hidden_leaks(clients):
    task = create(clients)
    response = clients["admin"].put(
        f"{P}/tasks/{task['id']}",
        json={
            "version": task["version"],
            "title": "Título atualizado",
            "description": "Descrição revisada",
            "supplier_id": 1,
            "priority": 9,
            "due": None,
        },
    )
    assert response.status_code == 200, response.text
    task = response.json()
    edits = [entry for entry in history(clients, task) if entry["action"] == "edited"]
    assert {"field": "title", "before": "Teste de aceite", "after": "Título atualizado"} in edits[
        -1
    ]["details"]["changes"]
    fields = [
        {"id": "public", "label": "Unidade", "type": "short_text"},
        {
            "id": "private",
            "label": "Campo confidencial",
            "type": "short_text",
            "visible_to": ["admin"],
            "editable_by": ["admin"],
        },
    ]
    task = schema(clients["admin"], task, fields, {"public": "Antes", "private": "VALOR RESTRITO"})
    response = clients["admin"].put(
        f"{P}/tasks/{task['id']}/values",
        json={
            "version": task["version"],
            "values": {"public": "Depois", "private": "SEGREDO NOVO"},
        },
    )
    assert response.status_code == 200, response.text
    task = response.json()
    admin_logs = history(clients, task)
    entry = [entry for entry in admin_logs if entry["action"] == "values_versioned"][-1]
    assert any(
        change["before"] == "Antes" and change["after"] == "Depois"
        for change in entry["details"]["changes"]
    )
    assert any(change["after"] == "SEGREDO NOVO" for change in entry["details"]["changes"])
    safe = str(history(clients, task, "no_grant"))
    assert (
        "SEGREDO NOVO" not in safe
        and "VALOR RESTRITO" not in safe
        and "Campo confidencial" not in safe
    )
    response = clients["admin"].post(
        f"{P}/tasks/{task['id']}/comments", json={"body": "Comentário de acompanhamento"}
    )
    assert response.status_code == 201
    entry = history(clients, task)[-1]
    assert (
        entry["action"] == "comment_added"
        and entry["details"]["body"] == "Comentário de acompanhamento"
    )
    assert entry["details"]["comment_id"] == response.json()["id"]
