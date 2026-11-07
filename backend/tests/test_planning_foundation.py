def test_hierarchy_releases_components_and_dependencies(clients):
    admin = clients["admin"]
    epic = admin.post("/api/v1/tasks", json={"title": "Iniciativa", "work_type": "epic"})
    assert epic.status_code == 201, epic.text
    task = admin.post(
        "/api/v1/tasks",
        json={"title": "Atividade filha", "work_type": "task", "parent_id": epic.json()["id"]},
    )
    assert task.status_code == 201, task.text
    assert task.json()["parent_id"] == epic.json()["id"]
    assert task.json()["work_type"] == "task"

    subtask = admin.post("/api/v1/tasks", json={"title": "Subtarefa", "work_type": "subtask"})
    assert subtask.status_code == 422

    release = admin.post(
        "/api/v1/releases",
        json={"name": "Entrega 1", "starts": "2026-11-01", "due": "2026-12-01"},
    )
    assert release.status_code == 201, release.text
    component = admin.post(
        "/api/v1/components", json={"name": "Portal", "description": "Área principal"}
    )
    assert component.status_code == 201, component.text
    links = admin.put(
        f"/api/v1/tasks/{task.json()['id']}/planning-links",
        params=[("releases", release.json()["id"]), ("components", component.json()["id"])],
    )
    assert links.status_code == 200, links.text
    assert links.json()["release_ids"] == [release.json()["id"]]
    assert links.json()["component_ids"] == [component.json()["id"]]

    dependency = admin.post(
        f"/api/v1/tasks/{task.json()['id']}/links",
        json={"target_task_id": epic.json()["id"], "link_type": "blocks"},
    )
    assert dependency.status_code == 201, dependency.text
    assert (
        admin.get(f"/api/v1/tasks/{task.json()['id']}").json()["links"][0]["task_id"]
        == epic.json()["id"]
    )


def test_link_added_and_removed_trigger_matching_automations(clients):
    admin = clients["admin"]
    source = admin.post("/api/v1/tasks", json={"title": "Origem da relação"}).json()
    target = admin.post("/api/v1/tasks", json={"title": "Destino da relação"}).json()
    created_rule = admin.post(
        "/api/v1/automations",
        json={
            "name": "Priorizar ao criar bloqueio",
            "trigger": "link_added",
            "conditions": {"link_types": ["blocks"]},
            "actions": [{"action": "set_priority", "config": {"priority": 4}}],
        },
    )
    assert created_rule.status_code == 201, created_rule.text
    removed_rule = admin.post(
        "/api/v1/automations",
        json={
            "name": "Priorizar ao remover bloqueio",
            "trigger": "link_removed",
            "conditions": {"link_types": ["blocks"]},
            "actions": [{"action": "set_priority", "config": {"priority": 5}}],
        },
    )
    assert removed_rule.status_code == 201, removed_rule.text

    link = admin.post(
        f"/api/v1/tasks/{source['id']}/links",
        json={"target_task_id": target["id"], "link_type": "blocks"},
    )
    assert link.status_code == 201, link.text
    assert admin.get(f"/api/v1/tasks/{source['id']}").json()["priority"] == 4

    deleted = admin.delete(f"/api/v1/tasks/{source['id']}/links/{link.json()['id']}")
    assert deleted.status_code == 200, deleted.text
    assert admin.get(f"/api/v1/tasks/{source['id']}").json()["priority"] == 5


def test_planning_permissions_and_capacity_validation(clients):
    denied = clients["no_grant"]
    assert denied.post("/api/v1/releases", json={"name": "Sem acesso"}).status_code == 403
    admin = clients["admin"]
    invalid = admin.post(
        "/api/v1/capacity",
        json={
            "supplier_id": 1,
            "user_id": 1,
            "starts": "2026-11-01",
            "ends": "2026-11-30",
            "minutes": 2400,
        },
    )
    assert invalid.status_code == 422
    created = admin.post(
        "/api/v1/capacity",
        json={
            "supplier_id": 1,
            "starts": "2026-11-01",
            "ends": "2026-11-30",
            "minutes": 2400,
            "notes": "Capacidade mensal",
        },
    )
    assert created.status_code == 201, created.text
    assert admin.get("/api/v1/capacity?starts=2026-11-15").json()[0]["minutes"] == 2400
    overlap = admin.post(
        "/api/v1/capacity",
        json={
            "supplier_id": 1,
            "starts": "2026-11-20",
            "ends": "2026-12-10",
            "minutes": 1200,
        },
    )
    assert overlap.status_code == 409


def test_internal_owner_and_capacity_forecast(clients):
    admin = clients["admin"]
    created = admin.post(
        "/api/v1/tasks",
        json={
            "title": "Demanda interna planejada",
            "supplier_id": 1,
            "assignee_user_id": 2,
            "estimate_policy": "optional",
        },
    )
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["assignee_user_id"] == 2
    supplier_task = clients["supplier"].get(f"/api/v1/tasks/{task['id']}")
    assert supplier_task.status_code == 200
    assert "assignee_user_id" not in supplier_task.json()
    supplier = clients["supplier"]
    moved = supplier.post(
        f"/api/v1/tasks/{task['id']}/move",
        json={"version": task["version"], "status": "todo", "priority": task["priority"]},
    )
    assert moved.status_code == 200, moved.text
    hours = supplier.put(
        f"/api/v1/tasks/{task['id']}/hours",
        json={"version": moved.json()["version"], "estimated_minutes": 600, "used_minutes": 0},
    )
    assert hours.status_code == 200, hours.text
    schedule = admin.put(
        f"/api/v1/tasks/{task['id']}/schedule",
        json={"version": hours.json()["version"], "planned_start": "2026-11-05", "due": "2026-11-18"},
    )
    assert schedule.status_code == 200, schedule.text
    capacity = admin.post(
        "/api/v1/capacity",
        json={
            "user_id": 2,
            "starts": "2026-11-01",
            "ends": "2026-11-30",
            "minutes": 1200,
        },
    )
    assert capacity.status_code == 201, capacity.text
    assert capacity.json()["demand_minutes"] == 600
    assert capacity.json()["demand_tasks"] == 1
    assert capacity.json()["utilization_percent"] == 50


def test_supplier_only_sees_releases_linked_to_owned_work(clients):
    admin = clients["admin"]
    own = admin.post("/api/v1/tasks", json={"title": "Tarefa atribuída", "supplier_id": 1}).json()
    other = admin.post("/api/v1/tasks", json={"title": "Tarefa alheia", "supplier_id": 2}).json()
    own_release = admin.post("/api/v1/releases", json={"name": "Entrega do fornecedor A"}).json()
    private_release = admin.post(
        "/api/v1/releases", json={"name": "Entrega do fornecedor B"}
    ).json()
    admin.put(f"/api/v1/tasks/{own['id']}/planning-links", params={"releases": own_release["id"]})
    admin.put(
        f"/api/v1/tasks/{other['id']}/planning-links", params={"releases": private_release["id"]}
    )
    visible = clients["supplier"].get("/api/v1/releases")
    assert visible.status_code == 200
    assert [row["name"] for row in visible.json()] == ["Entrega do fornecedor A"]


def test_workflow_restrictions_and_safe_automation(clients):
    admin = clients["admin"]
    transition = admin.post(
        "/api/v1/workflows/transitions",
        json={
            "source": "backlog",
            "target": "todo",
            "enabled": False,
            "roles": [],
            "required_fields": [],
        },
    )
    assert transition.status_code == 201, transition.text
    task = admin.post("/api/v1/tasks", json={"title": "Ação automática", "supplier_id": 1}).json()
    blocked = clients["supplier"].post(
        f"/api/v1/tasks/{task['id']}/move",
        json={"version": task["version"], "status": "todo", "priority": task["priority"]},
    )
    assert blocked.status_code == 409

    rule = admin.post(
        "/api/v1/automations",
        json={
            "name": "Prioridade operacional",
            "trigger": "card_created",
            "conditions": {"work_types": ["task"]},
            "action": "set_priority",
            "config": {"priority": 15},
            "enabled": True,
        },
    )
    assert rule.status_code == 201, rule.text
    automated = admin.post("/api/v1/tasks", json={"title": "Nova regra"})
    assert automated.status_code == 201, automated.text
    assert automated.json()["priority"] == 15
    history = admin.get(f"/api/v1/audit?entity=task&identity={automated.json()['id']}")
    assert history.status_code == 200
    assert any(row["action"] == "automation_applied" for row in history.json())


def test_agile_sprint_reports_are_derived_and_internal_only(clients):
    admin = clients["admin"]
    sprint = admin.post(
        "/api/v1/sprints",
        json={
            "name": "Sprint de relatório",
            "objective": "Demonstrar métricas",
            "starts": "2026-11-01",
            "ends": "2026-11-30",
        },
    )
    assert sprint.status_code == 201, sprint.text
    sprint_row = next(
        row for row in admin.get("/api/v1/sprints").json() if row["id"] == sprint.json()["id"]
    )
    task = admin.post(
        "/api/v1/tasks",
        json={"title": "Card do relatório", "supplier_id": 1, "estimate_policy": "optional"},
    ).json()
    linked = admin.post(
        f"/api/v1/sprints/{sprint.json()['id']}/tasks",
        json={
            "version": sprint_row["version"],
            "task_id": task["id"],
            "task_version": task["version"],
        },
    )
    assert linked.status_code == 200, linked.text
    task = clients["supplier"].put(
        f"/api/v1/tasks/{task['id']}/hours",
        json={"version": linked.json()["version"], "estimated_minutes": 180, "used_minutes": 0},
    )
    assert task.status_code == 200, task.text
    sprint_row = next(
        row for row in admin.get("/api/v1/sprints").json() if row["id"] == sprint.json()["id"]
    )
    started = admin.post(
        f"/api/v1/sprints/{sprint.json()['id']}/action",
        json={"version": sprint_row["version"], "action": "start"},
    )
    assert started.status_code == 200, started.text
    report = admin.get(f"/api/v1/reports/agile/{sprint.json()['id']}")
    assert report.status_code == 200, report.text
    assert report.json()["summary"]["committed_cards"] == 1
    assert report.json()["summary"]["planned_hours"] == 3
    assert report.json()["burndown"][-1]["remaining"] == 1
    assert report.json()["control_chart"]["sample_count"] == 0
    assert report.json()["control_chart"]["p85_days"] is None
    selected_cycle = admin.get(
        f"/api/v1/reports/agile/{sprint.json()['id']}?cycle_start_status=todo&cycle_end_status=review"
    )
    assert selected_cycle.status_code == 200, selected_cycle.text
    assert selected_cycle.json()["cycle_window"] == {
        "start_status": "todo",
        "end_status": "review",
    }
    invalid_cycle = admin.get(
        f"/api/v1/reports/agile/{sprint.json()['id']}?cycle_start_status=todo&cycle_end_status=todo"
    )
    assert invalid_cycle.status_code == 422
    assert (
        clients["supplier"].get(f"/api/v1/reports/agile/{sprint.json()['id']}").status_code == 403
    )


def test_shared_saved_views_are_scoped_to_selected_internal_roles(clients):
    view = clients["admin"].post(
        "/api/v1/board/views",
        json={
            "name": "Somente gestores",
            "layout": "table",
            "config": {},
            "shared": True,
            "shared_roles": ["manager"],
        },
    )
    assert view.status_code == 201, view.text
    manager_views = clients["manager"].get("/api/v1/board/views")
    assert manager_views.status_code == 200
    assert any(row["id"] == view.json()["id"] for row in manager_views.json())
    supplier_views = clients["supplier"].get("/api/v1/board/views")
    assert all(row["id"] != view.json()["id"] for row in supplier_views.json())

    widget = clients["admin"].post(
        "/api/v1/dashboard/widgets",
        json={
            "name": "Status para gestores",
            "group_by": "status",
            "measure": "count",
            "chart": "bar",
            "shared": True,
            "shared_roles": ["manager"],
        },
    )
    assert widget.status_code == 201, widget.text
    manager_dashboards = clients["manager"].get("/api/v1/dashboard/dashboards")
    shared_dashboard = next(row for row in manager_dashboards.json() if row["read_only"])
    manager_widgets = clients["manager"].get(
        f"/api/v1/dashboard/widgets?dashboard_id={shared_dashboard['id']}"
    )
    assert any(row["id"] == widget.json()["id"] for row in manager_widgets.json())
    supplier_widgets = clients["supplier"].get("/api/v1/dashboard/widgets")
    assert all(row["id"] != widget.json()["id"] for row in supplier_widgets.json())
    hidden_data = clients["supplier"].get(f"/api/v1/dashboard/widgets/{widget.json()['id']}/data")
    assert hidden_data.status_code == 403


def test_group_shared_views_and_widgets_are_limited_to_active_members(clients):
    admin = clients["admin"]
    created = admin.post(
        "/api/v1/user-groups", json={"name": "Produto", "description": "Equipe de produto"}
    )
    assert created.status_code == 201, created.text
    group_id = created.json()["id"]
    assert admin.put(
        f"/api/v1/user-groups/{group_id}/members", json={"user_ids": [2]}
    ).status_code == 200
    view = admin.post(
        "/api/v1/board/views",
        json={
            "name": "Visão Produto",
            "layout": "table",
            "config": {},
            "shared": True,
            "shared_group_ids": [group_id],
        },
    )
    assert view.status_code == 201, view.text
    assert any(row["id"] == view.json()["id"] for row in clients["manager"].get("/api/v1/board/views").json())
    assert all(row["id"] != view.json()["id"] for row in clients["no_grant"].get("/api/v1/board/views").json())
    assert all(row["id"] != view.json()["id"] for row in clients["supplier"].get("/api/v1/board/views").json())

    widget = admin.post(
        "/api/v1/dashboard/widgets",
        json={
            "name": "Cards Produto",
            "group_by": "status",
            "measure": "count",
            "chart": "bar",
            "shared": True,
            "shared_group_ids": [group_id],
        },
    )
    assert widget.status_code == 201, widget.text
    manager_dashboards = clients["manager"].get("/api/v1/dashboard/dashboards")
    shared_dashboard = next(row for row in manager_dashboards.json() if row["read_only"])
    assert any(
        row["id"] == widget.json()["id"]
        for row in clients["manager"].get(
            f"/api/v1/dashboard/widgets?dashboard_id={shared_dashboard['id']}"
        ).json()
    )
    assert clients["supplier"].get(f"/api/v1/dashboard/widgets/{widget.json()['id']}/data").status_code == 403

    deactivated = admin.put(
        f"/api/v1/user-groups/{group_id}",
        json={"name": "Produto", "description": "Equipe de produto", "active": False},
    )
    assert deactivated.status_code == 200
    assert all(row["id"] != view.json()["id"] for row in clients["manager"].get("/api/v1/board/views").json())


def test_tasks_api_accepts_status_category_query(clients):
    created = clients["admin"].post(
        "/api/v1/tasks",
        json={"title": "Filtro por categoria", "estimate_policy": "absent"},
    )
    assert created.status_code == 201, created.text
    identity = created.json()["id"]

    todo = clients["admin"].get(
        "/api/v1/tasks", params={"jql": 'statusCategory = "To Do"'}
    )
    progress = clients["admin"].get(
        "/api/v1/tasks", params={"jql": 'statusCategory = "In Progress"'}
    )
    assert todo.status_code == 200 and identity in {item["id"] for item in todo.json()}
    assert progress.status_code == 200 and identity not in {item["id"] for item in progress.json()}


def test_manager_can_configure_status_category_independent_of_column_order(clients):
    task = clients["admin"].post(
        "/api/v1/tasks",
        json={"title": "Categoria explícita", "estimate_policy": "absent"},
    )
    assert task.status_code == 201
    identity = task.json()["id"]

    changed = clients["manager"].put(
        "/api/v1/board/columns/backlog", json={"category": "in_progress"}
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["category"] == "in_progress"
    progress = clients["admin"].get(
        "/api/v1/tasks", params={"jql": 'statusCategory = "In Progress"'}
    )
    todo = clients["admin"].get(
        "/api/v1/tasks", params={"jql": 'statusCategory = "To Do"'}
    )
    assert identity in {row["id"] for row in progress.json()}
    assert identity not in {row["id"] for row in todo.json()}

    invalid_done = clients["manager"].put(
        "/api/v1/board/columns/backlog", json={"category": "done"}
    )
    assert invalid_done.status_code == 422
    denied = clients["supplier"].put(
        "/api/v1/board/columns/backlog", json={"category": "todo"}
    )
    assert denied.status_code == 403


def test_manager_can_set_and_clear_column_wip_limit(clients):
    manager = clients["manager"]
    limited = manager.put("/api/v1/board/columns/production", json={"wip_limit": 4})
    assert limited.status_code == 200, limited.text
    assert limited.json()["wip_limit"] == 4
    assert manager.get("/api/v1/board/columns").json()[2]["wip_limit"] == 4

    invalid = manager.put("/api/v1/board/columns/production", json={"wip_limit": 0})
    assert invalid.status_code == 422
    denied = clients["supplier"].put(
        "/api/v1/board/columns/production", json={"wip_limit": 2}
    )
    assert denied.status_code == 403

    cleared = manager.put("/api/v1/board/columns/production", json={"wip_limit": None})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["wip_limit"] is None


def test_dashboard_matrix_widget_returns_filtered_cross_tab_data(clients):
    admin = clients["admin"]
    first = admin.post(
        "/api/v1/tasks",
        json={"title": "Matriz: prioridade baixa", "priority": 1, "estimate_policy": "absent"},
    )
    second = admin.post(
        "/api/v1/tasks",
        json={"title": "Matriz: prioridade alta", "priority": 5, "estimate_policy": "absent"},
    )
    assert first.status_code == 201 and second.status_code == 201
    widget = admin.post(
        "/api/v1/dashboard/widgets",
        json={
            "name": "Status × prioridade",
            "group_by": "status",
            "group_by_secondary": "priority",
            "measure": "count",
            "chart": "matrix",
        },
    )
    assert widget.status_code == 201, widget.text
    assert widget.json()["group_by_secondary"] == "priority"
    response = admin.get(f"/api/v1/dashboard/widgets/{widget.json()['id']}/data")
    assert response.status_code == 200, response.text
    cells = {(row["row"], row["column"]): row["value"] for row in response.json()["data"]}
    assert cells[("Backlog", "Prioridade 1")] == 1
    assert cells[("Backlog", "Prioridade 5")] == 1


def test_dashboard_widget_order_is_personal_and_scope_checked(clients):
    admin = clients["admin"]
    first = admin.post(
        "/api/v1/dashboard/widgets",
        json={
            "name": "Primeiro gadget compartilhado",
            "group_by": "status",
            "shared": True,
            "shared_roles": ["manager"],
        },
    )
    second = admin.post(
        "/api/v1/dashboard/widgets",
        json={
            "name": "Segundo gadget compartilhado",
            "group_by": "priority",
            "shared": True,
            "shared_roles": ["manager"],
        },
    )
    assert first.status_code == second.status_code == 201
    first_id, second_id = first.json()["id"], second.json()["id"]

    manager = clients["manager"]
    manager_dashboards = manager.get("/api/v1/dashboard/dashboards")
    shared_dashboard = next(row for row in manager_dashboards.json() if row["read_only"])
    dashboard_id = shared_dashboard["id"]
    changed = manager.put(
        "/api/v1/dashboard/widgets/order",
        json={"dashboard_id": dashboard_id, "ids": [second_id, first_id]},
    )
    assert changed.status_code == 200, changed.text
    assert [row["id"] for row in manager.get(
        f"/api/v1/dashboard/widgets?dashboard_id={dashboard_id}"
    ).json()] == [second_id, first_id]
    assert [row["id"] for row in admin.get("/api/v1/dashboard/widgets").json()] == [
        first_id,
        second_id,
    ]
    stale = manager.put(
        "/api/v1/dashboard/widgets/order",
        json={"dashboard_id": dashboard_id, "ids": [first_id]},
    )
    assert stale.status_code == 409
    duplicate = manager.put(
        "/api/v1/dashboard/widgets/order",
        json={"dashboard_id": dashboard_id, "ids": [first_id, first_id]},
    )
    assert duplicate.status_code == 422


def test_field_changed_automation_filters_native_edits_and_records_trigger(clients):
    admin = clients["admin"]
    created = admin.post(
        "/api/v1/tasks", json={"title": "Gatilho por campo", "supplier_id": 1}
    )
    assert created.status_code == 201, created.text
    task = created.json()
    rule = admin.post(
        "/api/v1/automations",
        json={
            "name": "Ajustar prioridade após mudança",
            "trigger": "field_changed",
            "conditions": {"changed_fields": ["priority"]},
            "actions": [{"action": "set_priority", "config": {"priority": 5}}],
        },
    )
    assert rule.status_code == 201, rule.text

    def edit(current, *, title, priority):
        return admin.put(
            f"/api/v1/tasks/{current['id']}",
            json={
                "version": current["version"],
                "title": title,
                "description": current["description"],
                "supplier_id": current["supplier_id"],
                "assignee_user_id": current["assignee_user_id"],
                "due": current["due"],
                "priority": priority,
                "work_type": current["work_type"],
                "parent_id": current["parent_id"],
                "labels": current["labels"],
            },
        )

    title_edit = edit(task, title="Título editado", priority=0)
    assert title_edit.status_code == 200, title_edit.text
    assert title_edit.json()["priority"] == 0
    priority_edit = edit(title_edit.json(), title="Título editado", priority=2)
    assert priority_edit.status_code == 200, priority_edit.text
    assert priority_edit.json()["priority"] == 5

    audit = admin.get(
        "/api/v1/audit", params={"entity": "task", "identity": task["id"]}
    )
    assert audit.status_code == 200
    event = next(
        row
        for row in audit.json()
        if row["action"] == "automation_applied"
        and row["details"].get("trigger") == "field_changed"
    )
    assert event["details"]["changed_fields"] == ["priority"]

    custom_task = admin.post(
        "/api/v1/tasks", json={"title": "Gatilho de campo personalizado"}
    ).json()
    schema = admin.put(
        f"/api/v1/tasks/{custom_task['id']}/schema",
        json={
            "version": custom_task["version"],
            "fields": [{"id": "area", "label": "Área", "type": "short_text"}],
            "values": {},
        },
    )
    assert schema.status_code == 200, schema.text
    custom_rule = admin.post(
        "/api/v1/automations",
        json={
            "name": "Marcar área preenchida",
            "trigger": "field_changed",
            "conditions": {"changed_fields": ["area"]},
            "actions": [{"action": "set_priority", "config": {"priority": 4}}],
        },
    )
    assert custom_rule.status_code == 201, custom_rule.text
    values = admin.put(
        f"/api/v1/tasks/{custom_task['id']}/values",
        json={"version": schema.json()["version"], "values": {"area": "Operações"}},
    )
    assert values.status_code == 200, values.text
    assert values.json()["priority"] == 4
