"""Generate design-review artifacts using explicitly fictional data; never touches a database."""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from app.analytics import profile, summary
from app.analytics_exports import build_export

out = root / "artifacts" / "report-farol"
out.mkdir(parents=True, exist_ok=True)
reference = datetime(2026, 11, 5, 18, tzinfo=timezone.utc)
titles = [
    "Portal de atendimento ao empreendedor",
    "Revisão do catálogo de serviços",
    "Adequação de acessibilidade do portal",
    "Painel de acompanhamento de demandas",
    "Integração da base de conhecimento",
    "Homologação dos formulários digitais",
    "Revisão dos fluxos de atendimento",
    "Padronização dos indicadores operacionais",
]
states = [
    "backlog",
    "backlog",
    "todo",
    "production",
    "review",
    "done",
    "done",
    "production",
]
actors = {1: "Marina Exemplo · Gestão", 2: "Ana Exemplo · Fornecedor"}
cards = []
for i, (title, status) in enumerate(zip(titles, states), 1):
    start = reference - timedelta(days=12 + i)
    levels = ["backlog", "todo", "production", "review", "done"]
    events = [
        NS(
            id=1,
            created_at=start.isoformat(),
            action="created",
            details={"status": "backlog"},
            actor_id=1,
        )
    ]
    for index in range(1, levels.index(status) + 1):
        events.append(
            NS(
                id=index + 1,
                created_at=(start + timedelta(days=index * 2)).isoformat(),
                action="status_changed",
                details={
                    "origin": levels[index - 1],
                    "destination": levels[index],
                    "reason": "",
                },
                actor_id=1 if index in [1, 4] else 2,
            )
        )
    used = 480 if status == "done" else 360 if status in ["review", "production"] else 0
    submitted = (
        [
            NS(
                version=1,
                created_at=(start + timedelta(days=5)).isoformat(),
                estimated_minutes=600,
                used_minutes=used,
                author_id=2,
            )
        ]
        if used
        else []
    )
    decisions = (
        [
            NS(
                hours_version=1,
                created_at=(start + timedelta(days=7)).isoformat(),
                approved=True,
                reason="Entrega conferida",
                used_minutes=used,
                author_id=1,
            )
        ]
        if status == "done"
        else []
    )
    row = {
        "id": i,
        "title": title,
        "status": status,
        "created_at": start.isoformat(),
        "supplier_id": 1 if i % 2 else 2,
        "sprint_id": 1 if status != "backlog" else None,
        "priority": i,
        "due": (
            reference - timedelta(days=1)
            if status == "production"
            else reference + timedelta(days=5)
        )
        .date()
        .isoformat(),
        "fields": [
            {
                "id": "unit",
                "label": "Unidade solicitante",
                "type": "short_text",
                "required_for": [],
                "visible_to": ["admin", "manager"],
                "editable_by": ["admin", "manager"],
            }
        ],
        "values": {"unit": "Unidade de Desenvolvimento · Exemplo"},
        "estimated_minutes": 600 if status != "backlog" else 0,
        "used_minutes": used,
        "hours_version": 1 if used else 0,
        "approval": "approved" if status == "done" else "pending",
        "cost_cents": used * 12000 // 60 if status == "done" else 0,
        "rate_cents": 12000,
    }
    card = profile(row, events, submitted, decisions, reference, actors)
    card["supplier_name"] = "Ana Exemplo" if i % 2 else "Bruno Exemplo"
    cards.append(card)
totals = summary(cards, 7)
totals["recorded_flow"] = {
    "created": 8,
    "started": 5,
    "completed": 2,
    "returned": 0,
    "basis": "Eventos registrados dentro do recorte selecionado; não representa um censo geral.",
}
sprints = [
    {
        "id": 1,
        "name": "Sprint 08 · Experiência digital",
        "state": "active",
        "as_of": reference.isoformat(),
        "history_complete": True,
        "initial_cards": 5,
        "initial_done": 2,
        "commitment_percent": "40.00",
        "added_after_start": 1,
        "done": 2,
        "pending": 3,
        "returned": 0,
        "scope_cards": 5,
        "estimated_minutes": 3000,
        "used_minutes": 2040,
        "approved_minutes": 960,
        "estimated_cards": 5,
        "cost_cents": 192000,
        "completion_by_day": [
            {"day": "2026-11-02", "completed": 1},
            {"day": "2026-11-04", "completed": 1},
        ],
    }
]
data = {
    "items": cards,
    "total": len(cards),
    "as_of": reference.isoformat(),
    "filters": ["DADOS FICTÍCIOS · Exemplo de diagramação"],
    "period_basis": "Período seleciona a criação UTC dos cards. As durações abrangem o histórico até o corte observado.",
    "summary": totals,
    "sprints": sprints,
    "backlog_oldest": sorted(
        [c for c in cards if c["status"] == "backlog"], key=lambda c: c["created_at"]
    )[:10],
}
for fmt in ["html", "pdf"]:
    content, _ = build_export(
        fmt, data, True, {"starts": "2026-10-01", "ends": "2026-11-05"}
    )
    path = out / f"Gestao_Demandas_Exemplo_Farol.{fmt}"
    path.write_bytes(content.getvalue())
    print(path)
