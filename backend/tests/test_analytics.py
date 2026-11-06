from datetime import datetime, timezone, timedelta
from types import SimpleNamespace as NS
from io import BytesIO
import json
from openpyxl import load_workbook
from pypdf import PdfReader
from app.analytics import profile
from .test_acceptance import P, create, move, review, decision

BASE = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def event(identity, hour, action="status_changed", **details):
    return NS(
        id=identity,
        created_at=(BASE + timedelta(hours=hour)).isoformat(),
        action=action,
        details=details,
        actor_id=1,
    )


def row(status="done", **extra):
    return {
        "id": 1,
        "title": "Analise",
        "status": status,
        "created_at": BASE.isoformat(),
        "supplier_id": 1,
        "sprint_id": None,
        "priority": 0,
        "due": None,
        "fields": [],
        "values": {},
        "estimated_minutes": 0,
        "used_minutes": 60,
        "hours_version": 0,
        "approval": "pending",
        **extra,
    }


def history():
    return [
        event(1, 0, "created"),
        event(2, 1, origin="backlog", destination="todo"),
        event(3, 3, origin="todo", destination="production"),
        event(4, 8, origin="production", destination="review"),
        event(5, 10, origin="review", destination="done"),
    ]


def test_phase_seconds_lead_cycle_and_terminal_status():
    result = profile(row(), history(), [], [], BASE + timedelta(hours=12), {1: "Gestor"})
    assert result["history_complete"]
    assert {item["status"]: item["duration_seconds"] for item in result["phases"]} == {
        "backlog": 3600,
        "todo": 7200,
        "production": 18000,
        "review": 7200,
        "done": None,
    }
    assert result["lead_time_seconds"] == 36000
    assert result["cycles"][0]["duration_seconds"] == 25200
    assert result["current_phase_seconds"] is None
    assert result["age_seconds"] == 43200
    assert result["hours_deviation_minutes"] is None
    assert result["deadline"]["state"] == "no_due"


def test_reopening_preserves_cycles_and_excludes_time_in_done():
    events = history() + [
        event(6, 20, "reopened", reason="Corrigir", previous_cost_cents=96000),
        event(7, 20, origin="done", destination="review"),
        event(8, 23, origin="review", destination="done"),
    ]
    result = profile(row(), events, [], [], BASE + timedelta(hours=24), {1: "Gestor"})
    assert result["reopen_count"] == 1
    assert [cycle["duration_seconds"] for cycle in result["cycles"]] == [25200, 10800]
    assert result["lead_time_seconds"] == 36000
    assert (
        next(item for item in result["phases"] if item["status"] == "review")["duration_seconds"]
        == 18000
    )
    assert "previous_cost_cents" not in json.dumps(result)


def test_partial_or_missing_history_never_invents_duration():
    result = profile(row(), [], [], [], BASE + timedelta(hours=12), {})
    assert not result["history_complete"]
    assert result["current_phase_seconds"] is None and result["lead_time_seconds"] is None
    assert all(item["duration_seconds"] is None for item in result["phases"])
    events = history()
    del events[2]
    result = profile(row(), events, [], [], BASE + timedelta(hours=12), {})
    assert not result["history_complete"]
    assert (
        next(item for item in result["phases"] if item["status"] == "todo")["duration_seconds"]
        is None
    )


def test_automatic_sprint_moves_and_historical_cutoff():
    events = history()[:4]
    events[1] = event(2, 1, "included_in_sprint", sprint_id=1)
    events.append(event(5, 11, "returned_to_backlog", sprint_id=1, previous_status="review"))
    result = profile(
        row("review", read_only=True, sprint_id=1),
        events,
        [],
        [],
        BASE + timedelta(hours=40),
        {},
        (BASE + timedelta(hours=11)).isoformat(),
    )
    assert result["history_complete"]
    assert result["current_phase_seconds"] == 10800
    assert all(item["action"] != "returned_to_backlog" for item in result["timeline"])
    current = profile(row("backlog"), events, [], [], BASE + timedelta(hours=13), {})
    assert current["history_complete"] and current["current_phase_seconds"] == 7200


def test_approval_waits_are_versioned_and_never_use_estimate_as_cost():
    hours = [
        NS(
            version=1,
            created_at=(BASE + timedelta(hours=8)).isoformat(),
            author_id=1,
            used_minutes=60,
            estimated_minutes=120,
        ),
        NS(
            version=2,
            created_at=(BASE + timedelta(hours=10)).isoformat(),
            author_id=1,
            used_minutes=90,
            estimated_minutes=120,
        ),
    ]
    decisions = [
        NS(
            hours_version=1,
            created_at=(BASE + timedelta(hours=9)).isoformat(),
            author_id=2,
            approved=False,
            reason="Conferir",
        )
    ]
    result = profile(
        row("review", estimated_minutes=120, used_minutes=90, hours_version=2),
        history()[:4],
        hours,
        decisions,
        BASE + timedelta(hours=12),
        {1: "Fornecedor", 2: "Gestor"},
    )
    assert result["approval_history"][0]["waiting_seconds"] == 3600
    assert result["approval_history"][1]["waiting_seconds"] == 7200
    assert result["rejection_count"] == 1 and result["resubmission_count"] == 1
    assert result["approved_minutes"] == 0 and result["hours_deviation_minutes"] == -30
    assert result["hours_deviation_percent"] == "-25.00"


def test_api_scope_filters_and_financial_exports(clients):
    task = decision(clients, review(clients)).json()
    task = move(clients, task, "done").json()
    task = move(clients, task, "review", reason="Rever").json()
    other = create(clients, 2)
    manager = clients["manager"]
    result = manager.get(P + "/reports/analysis")
    assert result.status_code == 200, result.text
    assert result.json()["total"] == 2
    assert "cost_cents" in result.text
    assert manager.get(f"{P}/reports/cards/{other['id']}").status_code == 200
    detail = manager.get(f"{P}/reports/cards/{task['id']}")
    assert detail.status_code == 200 and detail.json()["reopen_count"] == 1
    assert "previous_cost_cents" not in detail.text
    for params, total in [
        ({"only_reopened": True}, 1),
        ({"approval_state": "approved"}, 0),
        ({"overdue_only": True}, 0),
        ({"min_phase_hours": "99999"}, 0),
    ]:
        response = manager.get(P + "/reports/analysis", params=params)
        assert response.status_code == 200, response.text
        assert response.json()["total"] == total
    for value in ["-1", "NaN", "Infinity"]:
        assert (
            manager.get(P + "/reports/analysis", params={"min_phase_hours": value}).status_code
            == 422
        )
    assert (
        clients["supplier"].get(P + "/exports/xlsx?analysis=true&financial=true").status_code == 403
    )
    exported = manager.get(P + "/exports/xlsx?analysis=true&only_reopened=true")
    assert exported.status_code == 200, exported.text
    book = load_workbook(BytesIO(exported.content))
    assert {
        "Cards",
        "Fases",
        "Linha do tempo",
        "Aprovações",
        "Sprints",
        "Backlog",
        "Definições",
    } <= set(book.sheetnames)
    assert book["Cards"].max_row == 2
    text = str([list(sheet.values) for sheet in book])
    assert "Tarifa" not in text and "Custo" not in text and "previous_cost_cents" not in text
    pdf = manager.get(P + "/exports/pdf?analysis=true")
    assert pdf.status_code == 200, pdf.text
    assert len(PdfReader(BytesIO(pdf.content)).pages) > 0
    admin_export = clients["admin"].get(P + "/exports/xlsx?analysis=true&financial=true")
    assert (
        "Custo consolidado (centavos)"
        in list(load_workbook(BytesIO(admin_export.content))["Cards"].values)[0]
    )


def test_sprint_commitment_scope_changes_and_closed_metrics(clients):
    admin = clients["admin"]
    first = create(clients)
    sprint = admin.post(
        P + "/sprints",
        json={
            "name": "Analise sprint",
            "objective": "Teste",
            "starts": "2026-01-01",
            "ends": "2026-01-15",
        },
    ).json()["id"]
    first = admin.post(
        f"{P}/sprints/{sprint}/tasks",
        json={"version": 1, "task_id": first["id"], "task_version": first["version"]},
    ).json()
    assert (
        admin.post(
            f"{P}/sprints/{sprint}/action", json={"version": 2, "action": "start"}
        ).status_code
        == 200
    )
    second = create(clients)
    assert (
        admin.post(
            f"{P}/sprints/{sprint}/tasks",
            json={"version": 3, "task_id": second["id"], "task_version": second["version"]},
        ).status_code
        == 200
    )
    response = admin.get(P + "/reports/analysis", params={"sprint_id": sprint})
    assert response.status_code == 200, response.text
    summary = response.json()["sprints"][0]
    assert summary["initial_cards"] == 1 and summary["added_after_start"] == 1
    assert summary["history_complete"]
    assert (
        admin.post(
            f"{P}/sprints/{sprint}/action", json={"version": 4, "action": "close"}
        ).status_code
        == 200
    )
    historical = admin.get(P + "/reports/analysis", params={"sprint_id": sprint}).json()
    assert historical["sprints"][0]["returned"] == 2
    assert all(card["status"] == "todo" and card["historical"] for card in historical["items"])
    assert all(card["history_complete"] for card in historical["items"])
    first_duration = historical["items"][0]["current_phase_seconds"]
    assert (
        admin.get(P + "/reports/analysis", params={"sprint_id": sprint}).json()["items"][0][
            "current_phase_seconds"
        ]
        == first_duration
    )
    current = admin.get(P + "/reports/analysis").json()
    assert current["summary"]["backlog"]["count"] == 2


def test_analysis_applies_custom_filters_and_pagination(clients):
    admin = clients["admin"]
    first = create(clients)
    create(clients)
    response = admin.put(
        f"{P}/tasks/{first['id']}/schema",
        json={
            "version": first["version"],
            "fields": [
                {"id": "region", "type": "select", "label": "Regiao", "options": ["Sul", "Norte"]}
            ],
            "values": {"region": "Sul"},
        },
    )
    assert response.status_code == 200
    conditions = json.dumps([{"field": "field:region", "op": "eq", "value": "Sul"}])
    response = admin.get(P + "/reports/analysis", params={"field_filters": conditions, "limit": 1})
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1 and response.json()["items"][0]["id"] == first["id"]
    response = admin.get(P + "/reports/analysis", params={"limit": 1, "offset": 1})
    assert response.json()["total"] == 2 and len(response.json()["items"]) == 1
    exported = admin.get(
        P + "/exports/xlsx", params={"analysis": True, "field_filters": conditions}
    )
    assert load_workbook(BytesIO(exported.content))["Cards"].max_row == 2


def test_html_report_scope_escaping_filters_and_portable_assets(clients, tmp_path):
    task = (
        clients["admin"]
        .post(P + "/tasks", json={"title": "<script>alert(1)</script> Relatório", "supplier_id": 1})
        .json()
    )
    other = (
        clients["admin"]
        .post(P + "/tasks", json={"title": "SEGREDO OUTRO FORNECEDOR", "supplier_id": 2})
        .json()
    )
    supplier = clients["supplier"]
    response = clients["manager"].get(P + "/exports/html")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/html")
    assert "os-manager.html" in response.headers["content-disposition"]
    html = response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html
    assert other["title"] in html
    assert "Custo consolidado" not in html and "rate_cents" not in html
    assert "data:font/woff2;base64," in html and "data:image/svg+xml;base64," in html
    assert "prefers-reduced-motion" in html and "default-src 'none'" in html
    assert html.count("<h1>") == 1
    assert supplier.get(P + "/exports/html?financial=true").status_code == 403
    filtered = clients["manager"].get(P + "/exports/html", params={"only_reopened": True})
    assert task["title"] not in filtered.text
    assert "Nenhum card encontrado" in filtered.text
    admin = clients["admin"].get(P + "/exports/html?financial=true")
    assert admin.status_code == 200 and "Custo consolidado" in admin.text
    (tmp_path / "report.html").write_text(admin.text, encoding="utf-8")
    preview_pdf = clients["admin"].get(P + "/exports/pdf?analysis=true&financial=true")
    assert preview_pdf.status_code == 200
    (tmp_path / "report.pdf").write_bytes(preview_pdf.content)


def test_supplier_cannot_consult_or_export_reports(clients):
    own = create(clients)
    other = create(clients, 2)
    for client in [clients["supplier"], clients["other"]]:
        paths = [
            "/reports/fields",
            "/reports/preview",
            "/reports/analysis",
            f"/reports/cards/{own['id']}",
            f"/reports/cards/{other['id']}",
        ]
        paths += [
            f"/exports/{fmt}{query}"
            for fmt in ["xlsx", "pdf", "html"]
            for query in ["", "?analysis=true", "?financial=true"]
        ]
        for path in paths:
            response = client.get(P + path)
            assert response.status_code == 403, (path, response.text)
            assert "Teste de aceite" not in response.text
    assert clients["supplier"].get(f"{P}/tasks/{own['id']}").status_code == 200
    assert clients["supplier"].get(f"{P}/tasks/{other['id']}").status_code == 404


def test_editorial_exports_empty_cohort_and_print_sections(clients):
    html = clients["admin"].get(P + "/exports/html")
    assert html.status_code == 200
    assert "Sem base" in html.text and "Nenhum card encontrado" in html.text
    assert "Expandir cards" in html.text and "Recolher cards" in html.text
    assert "report-nav" in html.text and "synthesis" in html.text
    pdf = clients["admin"].get(P + "/exports/pdf?analysis=true")
    assert pdf.status_code == 200
    reader = PdfReader(BytesIO(pdf.content))
    text = " ".join(page.extract_text() for page in reader.pages)
    assert "Sem base" in text and "Nenhum registro neste recorte." in text
    assert "Custo consolidado" not in text
    assert all("Gestão de Demandas /" in page.extract_text() for page in reader.pages)
