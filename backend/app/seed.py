"""Explicit fictitious seed. Public test deployments must supply a private password."""

import os
from sqlalchemy import select
from .db import SessionLocal
from .models import User, Role, Permission, Supplier, Rate, Task, Sprint
from .security import hasher, PERMISSIONS
from .services import set_supplier


def run():
    if os.getenv("OS_MANAGER_ALLOW_DEMO_SEED") != "true":
        raise SystemExit("Defina OS_MANAGER_ALLOW_DEMO_SEED=true somente em desenvolvimento.")
    password = os.getenv("OS_MANAGER_DEMO_PASSWORD", "DemoLocal!2026")
    if os.getenv("CLOUD_DEPLOYMENT") == "true":
        from .start import validate_environment

        validate_environment(os.environ)
    with SessionLocal.begin() as db:
        if db.scalar(select(User.id).limit(1)):
            print("Seed não aplicado: já existem usuários; nenhum dado foi alterado.")
            return
        db.add_all([Role(id=role) for role in ["admin", "manager", "internal", "supplier"]])
        db.add_all([Permission(id=permission) for permission in sorted(PERMISSIONS)])
        db.flush()
        accounts = [
            ("admin", "admin", []),
            (
                "gestor",
                "manager",
                [
                    "create_tasks",
                    "configure_cards",
                    "manage_sprints",
                    "reopen_sprints",
                    "manage_suppliers",
                    "change_rates",
                    "approve_hours",
                    "view_financial",
                    "export_financial",
                    "export_data",
                ],
            ),
            (
                "gestor_sem_aprovacao",
                "manager",
                ["create_tasks", "manage_sprints", "export_data"],
            ),
            (
                "interno",
                "internal",
                ["create_tasks", "configure_cards", "manage_sprints", "export_data"],
            ),
            ("fornecedor", "supplier", []),
            ("fornecedor2", "supplier", []),
        ]
        users = {}
        for username, role, grants in accounts:
            row = User(
                username=username,
                role=role,
                grants=grants,
                password_hash=hasher.hash(password),
            )
            db.add(row)
            db.flush()
            users[username] = row
        supplier = Supplier(
            name="Ana Exemplo",
            function="Desenvolvimento",
            user_id=users["fornecedor"].id,
        )
        second = Supplier(name="Bruno Exemplo", function="Design", user_id=users["fornecedor2"].id)
        db.add_all([supplier, second])
        db.flush()
        db.add_all(
            [
                Rate(
                    supplier_id=supplier.id,
                    cents=12000,
                    author_id=users["admin"].id,
                    reason="Valor fictício para demonstração",
                ),
                Rate(
                    supplier_id=second.id,
                    cents=9000,
                    author_id=users["admin"].id,
                    reason="Valor fictício",
                ),
            ]
        )
        db.flush()
        for title, owner in [
            ("Portal de atendimento", supplier.id),
            ("Revisar acessibilidade", supplier.id),
            ("Desenhar fluxo de solicitações", second.id),
        ]:
            task = Task(
                title=title,
                description="Demanda fictícia para explorar o fluxo do OS Manager.",
                creator_id=users["admin"].id,
            )
            db.add(task)
            db.flush()
            set_supplier(db, users["admin"], task, owner)
        db.add(
            Sprint(
                name="Sprint de demonstração",
                objective="Validar o fluxo local com dados fictícios",
                starts="2026-10-15",
                ends="2026-10-29",
                owner_id=users["gestor"].id,
            )
        )
    print("Seed fictício criado. Use a senha configurada; nenhum segredo foi registrado.")


if __name__ == "__main__":
    run()
