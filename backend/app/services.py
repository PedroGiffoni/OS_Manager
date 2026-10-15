from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException
from sqlalchemy import select
from .models import (
    Task,
    Supplier,
    Rate,
    Assignment,
    Sprint,
    SchemaVersion,
    Audit,
    Approval,
    User,
    Attachment,
)
from .security import allowed, supplier_for

STATUSES = ["backlog", "todo", "production", "review", "done"]


def fail(message, status=422, code="BUSINESS_RULE"):
    raise HTTPException(status, {"code": code, "message": message})


def audit(db, actor, entity, identity, action, **details):
    db.add(
        Audit(
            actor_id=actor.id,
            entity=entity,
            entity_id=identity,
            action=action,
            details=details,
        )
    )


def version(row, expected):
    if row.version != expected:
        fail(
            "Registro alterado por outra sessão. Atualize e tente novamente.",
            409,
            "CONFLICT",
        )


def scoped_tasks(db, user):
    query = select(Task).where(Task.archived.is_(False))
    if user.role == "supplier":
        supplier = supplier_for(db, user)
        query = query.where(Task.supplier_id == (supplier.id if supplier else -1))
    return query


def get_task(db, user, identity, writable=False):
    task = db.scalar(scoped_tasks(db, user).where(Task.id == identity))
    if not task:
        fail("Atividade não encontrada.", 404, "NOT_FOUND")
    if writable and task.sprint_id and db.get(Sprint, task.sprint_id).state == "closed":
        fail("Sprint encerrada é somente leitura.", 409)
    return task


def current_schema(db, task):
    return db.scalar(
        select(SchemaVersion)
        .where(SchemaVersion.task_id == task.id)
        .order_by(SchemaVersion.version.desc())
    )


def assignment(db, task):
    return db.scalar(
        select(Assignment).where(Assignment.task_id == task.id, Assignment.active_key == "active")
    )


def set_supplier(db, user, task, identity):
    if task.supplier_id == identity:
        return
    if task.status not in {"backlog", "todo"} or task.used_minutes or task.hours_version:
        fail(
            "Troca de fornecedor permitida apenas antes de apontamentos e produção.",
            409,
        )
    previous = assignment(db, task)
    if previous:
        previous.active_key = None
        db.flush()
    if identity is not None:
        supplier = db.get(Supplier, identity)
        if not supplier or not supplier.active:
            fail("Fornecedor indisponível.")
        rate = db.scalar(select(Rate).where(Rate.supplier_id == identity).order_by(Rate.id.desc()))
        if not rate:
            fail("Fornecedor sem tarifa vigente.")
        db.add(
            Assignment(
                task_id=task.id,
                supplier_id=identity,
                rate_id=rate.id,
                rate_cents=rate.cents,
            )
        )
    task.supplier_id = identity
    audit(db, user, "task", task.id, "assignment_changed", supplier_id=identity)


def cost_cents(db, task, sprint_id=None):
    if task.approval != "approved":
        return 0
    approval = db.scalar(
        select(Approval).where(
            Approval.task_id == task.id,
            Approval.hours_version == task.hours_version,
            Approval.approved.is_(True),
        )
    )
    if not approval or (sprint_id is not None and approval.sprint_id != sprint_id):
        return 0
    snapshot = db.get(Assignment, approval.assignment_id)
    return int(
        (Decimal(approval.used_minutes) * Decimal(snapshot.rate_cents) / Decimal(60)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def task_payload(db, user, task):
    result = {
        key: getattr(task, key)
        for key in (
            "id",
            "title",
            "description",
            "status",
            "priority",
            "due",
            "supplier_id",
            "sprint_id",
            "estimated_minutes",
            "used_minutes",
            "hours_version",
            "approval",
            "version",
            "created_at",
        )
    }
    decision = db.scalar(
        select(Approval).where(Approval.task_id == task.id).order_by(Approval.id.desc())
    )
    result["approval_reason"] = decision.reason if decision and not decision.approved else ""
    schema = current_schema(db, task)
    visible = (
        [field for field in schema.fields if user.role in field["visible_to"]] if schema else []
    )
    result["fields"] = visible
    result["values"] = (
        {field["id"]: field_value(task, schema, field) for field in visible} if schema else {}
    )
    if allowed(user, "view_financial") and user.role in {"admin", "manager"}:
        snapshot = assignment(db, task)
        result["rate_cents"] = snapshot.rate_cents if snapshot else None
        result["cost_cents"] = cost_cents(db, task)
    return result


def validate_fields(fields, values):
    ids = {field["id"] for field in fields}
    if len(ids) != len(fields) or set(values) - ids:
        fail("Campos duplicados ou valores sem definição.")
    for field in fields:
        kind, value = field["type"], values.get(field["id"])
        if kind not in {
            "short_text",
            "long_text",
            "number",
            "date",
            "select",
            "checkbox",
            "user",
            "supplier",
            "attachment",
            "native",
        }:
            fail("Tipo de campo indisponível nesta versão.")
        if set(field["required_for"]) - set(STATUSES):
            fail("Etapa inválida na obrigatoriedade.")
        roles = {"admin", "manager", "internal", "supplier"}
        if set(field["visible_to"]) - roles or set(field["editable_by"]) - roles:
            fail("Perfil inválido no campo.")
        if kind == "native":
            if field.get("native_key") not in {
                "id",
                "title",
                "status",
                "supplier_id",
                "sprint_id",
                "estimated_minutes",
                "used_minutes",
                "approval",
            }:
                fail("Campo nativo inválido.")
            if value is not None and value != "":
                fail("Campos nativos são alterados apenas pelos endpoints estruturais.")
            continue
        if value is None or value == "":
            continue
        if kind in {"short_text", "long_text", "select", "date"} and not isinstance(value, str):
            fail("Valor deve ser texto: " + field["label"])
        if kind == "number":
            try:
                number = Decimal(str(value))
                if not number.is_finite():
                    raise ValueError()
            except Exception:
                fail("Número inválido: " + field["label"])
        if kind == "checkbox" and not isinstance(value, bool):
            fail("Checkbox deve ser booleano.")
        if kind == "select" and value not in field["options"]:
            fail("Opção inválida: " + field["label"])
        if kind == "date":
            try:
                date.fromisoformat(value)
            except ValueError:
                fail("Data inválida.")
        if isinstance(value, str) and len(value) > 10000:
            fail("Valor de campo excede o limite.")


def move_task(db, user, task, data):
    version(task, data.version)
    if data.status not in STATUSES:
        fail("Etapa inválida.")
    manager = user.role in {"admin", "manager"}
    supplier = supplier_for(db, user)
    if not manager and not (
        user.role == "supplier" and supplier and supplier.id == task.supplier_id
    ):
        fail("Sem autorização para mover esta atividade.", 403)
    origin = task.status
    if data.status == origin:
        task.priority = data.priority
        task.version += 1
        audit(db, user, "task", task.id, "reordered", priority=data.priority)
        return
    if origin == "done":
        if not manager or data.status != "review" or not data.reason:
            fail("Reabertura exige gestor, destino Em revisão e justificativa.", 403)
        audit(
            db,
            user,
            "task",
            task.id,
            "reopened",
            reason=data.reason,
            previous_cost_cents=cost_cents(db, task),
            hours_version=task.hours_version,
        )
        task.approval = "pending"
        task.hours_version += 1
    else:
        if STATUSES.index(data.status) != STATUSES.index(origin) + 1:
            fail("Retornos e saltos de etapa não estão autorizados nesta versão.")
        if data.status == "production" and task.estimated_minutes <= 0:
            fail("Preencha as horas previstas para mover esta atividade para Em produção.")
        if data.status == "review" and task.used_minutes <= 0:
            fail("Preencha as horas utilizadas para mover esta atividade para Em revisão.")
        if data.status == "done" and (not manager or task.approval != "approved"):
            fail("Conclusão exige gestor e horas aprovadas.", 403)
    schema = current_schema(db, task)
    if schema:
        missing = [
            field["label"]
            for field in schema.fields
            if data.status in field["required_for"]
            and (
                field_value(task, schema, field) is None
                or field_value(task, schema, field) == ""
                or (field["type"] == "checkbox" and field_value(task, schema, field) is not True)
                or (field["type"] == "attachment" and not field_value(task, schema, field))
            )
        ]
        if missing:
            fail("Preencha os campos obrigatórios: " + ", ".join(missing))
    task.status, task.priority = data.status, data.priority
    audit(
        db,
        user,
        "task",
        task.id,
        "status_changed",
        origin=origin,
        destination=data.status,
        reason=data.reason,
    )


def validate_references(db, user, task, fields, values):
    for field in fields:
        value = values.get(field["id"])
        if value in (None, ""):
            continue
        if field["type"] in {"user", "supplier"}:
            if isinstance(value, bool) or not isinstance(value, int):
                fail("Referência inválida: " + field["label"])
            reference = db.get(User if field["type"] == "user" else Supplier, value)
            if not reference or not reference.active:
                fail("Referência indisponível.")
            if user.role == "supplier" and (
                (field["type"] == "user" and value != user.id)
                or (field["type"] == "supplier" and value != task.supplier_id)
            ):
                fail("Referência fora do seu escopo.", 403)
        if field["type"] == "attachment":
            if not isinstance(value, list) or len(value) > 30:
                fail("Anexos devem ser uma lista de identificadores.")
            for identity in value:
                if isinstance(identity, bool) or not isinstance(identity, int):
                    fail("Identificador de anexo inválido.")
                attachment = db.get(Attachment, identity)
                if not attachment or attachment.task_id != task.id:
                    fail("Anexo fora desta atividade.", 403)


def field_value(task, schema, field):
    return (
        getattr(task, field["native_key"])
        if field["type"] == "native"
        else schema.values.get(field["id"])
    )
