P = "/api/v1"


def test_only_admin_can_create_boards_and_manage_members(clients):
    denied = clients["manager"].post(P + "/boards", json={"name": "Interno", "user_ids": [2]})
    assert denied.status_code == 403

    created = clients["admin"].post(
        P + "/boards",
        json={"name": "Demandas internas", "description": "Trabalho do setor", "user_ids": [2]},
    )
    assert created.status_code == 201, created.text
    board_id = created.json()["id"]
    assert created.json()["members"][0]["username"] == "manager"

    # Admin membership edits must work even while the selected context is another board.
    updated = clients["admin"].put(
        f"{P}/boards/{board_id}",
        json={"name": "Demandas internas", "description": "Trabalho do setor", "user_ids": [2, 4]},
    )
    assert updated.status_code == 200, updated.text
    assert {member["id"] for member in updated.json()["members"]} == {2, 4}

    visible = clients["manager"].get(P + "/boards").json()
    assert board_id in {board["id"] for board in visible}
    denied_update = clients["manager"].put(
        f"{P}/boards/{board_id}",
        json={"name": "Alterado", "description": "", "user_ids": [2]},
    )
    assert denied_update.status_code == 403


def test_board_isolation_and_supplier_assignment_scope(clients):
    board = clients["admin"].post(
        P + "/boards",
        json={"name": "Demandas terceirizadas", "user_ids": [2, 4]},
    )
    assert board.status_code == 201, board.text
    board_id = board.json()["id"]

    manager = clients["manager"]
    manager.headers["X-Board-ID"] = str(board_id)
    own = manager.post(P + "/tasks", json={"title": "Atividade do novo quadro", "supplier_id": 1})
    other_supplier = manager.post(P + "/tasks", json={"title": "Outra atividade", "supplier_id": 2})
    assert own.status_code == 201, own.text
    assert other_supplier.status_code == 201, other_supplier.text

    admin = clients["admin"]
    assert admin.get(f"{P}/tasks/{own.json()['id']}").status_code == 404
    admin.headers["X-Board-ID"] = str(board_id)
    assert admin.get(f"{P}/tasks/{own.json()['id']}").status_code == 200
    columns = admin.get(P + "/board/columns").json()
    assert {column["key"] for column in columns} >= {"backlog", "todo", "production", "review", "done"}

    unassigned_user = clients["no_grant"]
    unassigned_user.headers["X-Board-ID"] = str(board_id)
    assert unassigned_user.get(P + "/tasks").status_code == 403

    supplier = clients["supplier"]
    supplier.headers["X-Board-ID"] = str(board_id)
    visible = supplier.get(P + "/tasks").json()
    assert [task["title"] for task in visible] == ["Atividade do novo quadro"]
    assert supplier.get(f"{P}/tasks/{other_supplier.json()['id']}").status_code == 404
