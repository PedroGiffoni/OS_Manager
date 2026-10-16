"""Typed filters over authorized report records, independent of the database dialect."""

import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from .models import Attachment, Supplier, Sprint, User
from .security import allowed
from .services import fail

STATUSES = {
    "backlog": "Backlog",
    "todo": "A fazer",
    "production": "Em produção",
    "review": "Em revisão",
    "done": "Concluído",
}
APPROVALS = {
    "pending": "Aguardando aprovação",
    "approved": "Aprovado",
    "rejected": "Rejeitado",
    "resubmitted": "Reapresentado",
}
NATIVE = {
    "id": ("Identificador", "number"),
    "title": ("Título", "short_text"),
    "status": ("Etapa", "select"),
    "priority": ("Prioridade", "number"),
    "due": ("Prazo", "date"),
    "created_at": ("Data de criação (UTC)", "date"),
    "supplier_id": ("Fornecedor responsável", "supplier"),
    "sprint_id": ("Sprint", "sprint"),
    "creator_id": ("Criador", "user"),
    "estimated_minutes": ("Horas previstas", "hours"),
    "used_minutes": ("Horas utilizadas", "hours"),
    "approval": ("Aprovação de horas", "select"),
    "attachments": ("Anexos da atividade", "attachment"),
    "rate_cents": ("Tarifa congelada (R$/h)", "money"),
    "cost_cents": ("Custo aprovado (R$)", "money"),
}


class ReportFilter(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    field: str = Field(min_length=1, max_length=100)
    op: str = Field(min_length=1, max_length=20)
    value: str = Field(default="", max_length=2000)
    value_to: str = Field(default="", max_length=2000)


def operators(kind):
    if kind in {"number", "hours", "money", "date"}:
        return ["eq", "gte", "lte", "between", "empty", "not_empty"]
    if kind in {"select", "checkbox", "user", "supplier", "sprint"}:
        return ["eq", "empty", "not_empty"]
    return ["contains", "eq", "empty", "not_empty"]


def decimal(value):
    try:
        if len(str(value)) > 100:
            raise ValueError
        result = Decimal(str(value).replace(",", "."))
        if not result.is_finite() or abs(result) > Decimal("1000000000000"):
            raise ValueError
        return result
    except (InvalidOperation, ValueError):
        fail("Informe um número válido no filtro.")


def scalar(value, kind):
    if kind in {"number", "hours", "money"}:
        return decimal(value)
    if kind == "date":
        try:
            return date.fromisoformat(value)
        except ValueError:
            fail("Informe uma data válida no filtro.")
    if kind == "checkbox":
        if value not in {"true", "false"}:
            fail("Selecione Sim ou Não no filtro.")
        return value == "true"
    return value.casefold().strip()


def parse_filters(raw, definitions):
    try:
        data = json.loads(raw or "[]")
        if not isinstance(data, list) or len(data) > 30:
            raise ValueError
        filters = [ReportFilter.model_validate(item) for item in data]
    except (ValueError, ValidationError, TypeError):
        fail("Filtros inválidos. Use até 30 condições válidas.")
    indexed = {item["key"]: item for item in definitions}
    for item in filters:
        definition = indexed.get(item.field)
        if not definition:
            fail("Campo de filtro indisponível para seu acesso.", 403)
        if item.op not in definition["operators"]:
            fail("Operador inválido para o tipo do campo.")
        if item.op not in {"empty", "not_empty"}:
            if not item.value.strip():
                fail("Preencha o valor do filtro.")
            first = scalar(item.value, definition["type"])
            if definition["type"] in {"user", "supplier", "sprint"}:
                if not item.value.isdigit() or int(item.value) <= 0:
                    fail("Selecione uma referência válida no filtro.")
            if definition["type"] == "select" and item.value not in {
                option["value"] for option in definition["options"]
            }:
                fail("Opção de filtro inválida.")
            if item.op == "between":
                last = scalar(item.value_to, definition["type"])
                if last < first:
                    fail("O limite final do filtro deve ser maior ou igual ao inicial.")
    return filters


def catalogue(db, user, rows):
    financial = user.role in {"admin", "manager"} and allowed(user, "view_financial")
    definitions = {}
    for key, (label, kind) in NATIVE.items():
        if key in {"rate_cents", "cost_cents"} and not financial:
            continue
        definitions["native:" + key] = {
            "key": "native:" + key,
            "label": label,
            "type": kind,
            "options": [],
            "financial": kind == "money",
            "source": "native",
        }
    for row in rows:
        for field in row["fields"]:
            if field["type"] == "native":
                continue
            key = "field:" + field["id"]
            if key not in definitions:
                definitions[key] = {
                    "key": key,
                    "label": field["label"],
                    "type": field["type"],
                    "options": [],
                    "financial": False,
                    "source": "custom",
                    "tasks": [],
                }
            item = definitions[key]
            if item["type"] != field["type"]:
                continue
            item["tasks"].append(row["id"])
            for option in field.get("options", []):
                if option not in [entry["value"] for entry in item["options"]]:
                    item["options"].append({"value": option, "label": option})
    for item in definitions.values():
        kind = item["type"]
        key = item["key"]
        if key == "native:status":
            item["options"] = [
                {"value": value, "label": label} for value, label in STATUSES.items()
            ]
        elif key == "native:approval":
            item["options"] = [
                {"value": value, "label": label} for value, label in APPROVALS.items()
            ]
        elif kind == "checkbox":
            item["options"] = [
                {"value": "true", "label": "Sim"},
                {"value": "false", "label": "Não"},
            ]
        elif kind in {"supplier", "user", "sprint"}:
            values = set()
            for row in rows:
                value, available = field_value(row, item)
                if available and value is not None:
                    values.add(int(value))
            model = {"supplier": Supplier, "user": User, "sprint": Sprint}[kind]
            names = (
                {
                    value.id: (value.username if kind == "user" else value.name)
                    for value in db.scalars(select(model).where(model.id.in_(values)))
                }
                if values
                else {}
            )
            item["options"] = [
                {"value": str(value), "label": names.get(value, str(value))}
                for value in sorted(values)
            ]
        item["operators"] = operators(kind)
    labels = {}
    for item in definitions.values():
        labels[item["label"]] = labels.get(item["label"], 0) + 1
    for item in definitions.values():
        if item["source"] == "custom" and labels[item["label"]] > 1:
            item["label"] += " · cards " + ", ".join(
                "OS-" + str(value) for value in item["tasks"][:3]
            )
        item.pop("tasks", None)
    return list(definitions.values())


def field_value(row, definition):
    key = definition["key"]
    if key.startswith("native:"):
        native = key[7:]
        return (
            row.get("report_attachments", []) if native == "attachments" else row.get(native)
        ), True
    field = next(
        (
            field
            for field in row["fields"]
            if "field:" + field["id"] == key and field["type"] == definition["type"]
        ),
        None,
    )
    return (row["values"].get(field["id"]), True) if field else (None, False)


def apply_filters(db, rows, filters, definitions):
    if not filters:
        return rows
    indexed = {item["key"]: item for item in definitions}
    attachment_names = {}
    if any(indexed[item.field]["type"] == "attachment" for item in filters) and rows:
        for attachment in db.execute(
            select(Attachment.id, Attachment.task_id, Attachment.name).where(
                Attachment.task_id.in_([row["id"] for row in rows])
            )
        ):
            attachment_names[attachment.id] = (attachment.task_id, attachment.name)
        for row in rows:
            row["report_attachments"] = [
                name for task_id, name in attachment_names.values() if task_id == row["id"]
            ]

    def matches(row, item):
        definition = indexed[item.field]
        value, available = field_value(row, definition)
        if not available:
            return False
        kind = definition["type"]
        empty = value is None or value == "" or value == [] or (kind == "hours" and value == 0)
        if item.op == "empty":
            return empty
        if item.op == "not_empty":
            return not empty
        if empty:
            return False
        if kind == "attachment":
            if item.field.startswith("field:"):
                value = [
                    attachment_names[identity][1]
                    for identity in value
                    if identity in attachment_names and attachment_names[identity][0] == row["id"]
                ]
            return any(
                (
                    item.value.casefold() in name.casefold()
                    if item.op == "contains"
                    else item.value.casefold() == name.casefold()
                )
                for name in value
            )
        if kind in {"hours", "money"}:
            value = decimal(value) / (60 if kind == "hours" else 100)
        elif kind == "number":
            value = decimal(value)
        elif kind == "date":
            value = date.fromisoformat(str(value)[:10])
        elif kind != "checkbox":
            value = str(value).casefold().strip()
        expected = scalar(item.value, kind)
        if item.op == "contains":
            return expected in value
        if item.op == "eq":
            return value == expected
        if item.op == "gte":
            return value >= expected
        if item.op == "lte":
            return value <= expected
        return expected <= value <= scalar(item.value_to, kind)

    return [row for row in rows if all(matches(row, item) for item in filters)]


def filter_context(db, user, raw, sprint_id=None):
    from .reporting import records

    if not raw or raw == "[]":
        return [], []
    definitions = catalogue(db, user, records(db, user, sprint_id=sprint_id))
    return parse_filters(raw, definitions), definitions


def filter_summary(filters, definitions):
    indexed = {item["key"]: item for item in definitions}
    labels = {
        "contains": "contém",
        "eq": "igual a",
        "gte": "a partir de",
        "lte": "até",
        "between": "entre",
        "empty": "não preenchido",
        "not_empty": "preenchido",
    }
    result = []
    for item in filters:
        definition = indexed[item.field]
        options = {option["value"]: option["label"] for option in definition["options"]}
        value = options.get(item.value, item.value)
        result.append(
            f"{definition['label']} {labels[item.op]} {value}"
            + (f" e {item.value_to}" if item.op == "between" else "")
        )
    return result
