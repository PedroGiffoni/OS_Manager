from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException
from sqlalchemy import select
from .audit_trail import notify_task_watchers, record_task_changes
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
    KanbanColumn,
    TaskRelease,
    TaskComponent,
    TaskDependency,
    WorkflowTransition,
    Hours,
)
from .security import active_internal_user, allowed, supplier_for
from .workflows import apply_transition_actions, conditions_match, transition_policy

STATUSES = ["backlog", "todo", "production", "review", "done"]


def fail(message, status=422, code="BUSINESS_RULE"):
    raise HTTPException(status, {"code": code, "message": message})


def audit(db, actor, entity, identity, action, *, timestamp=None, **details):
    details["actor_name"] = actor.username
    audit_row = Audit(
        board_id=identity if entity == "board" else db.info.get("board_id"),
        actor_id=actor.id,
        entity=entity,
        entity_id=identity,
        action=action,
        details=details,
        **({"created_at": timestamp} if timestamp else {}),
    )
    db.add(audit_row)
    record_task_changes(db, audit_row, entity, action, details)
    if entity == "task":
        notify_task_watchers(db, actor, identity, action, timestamp)


def blocking_path_exists(db, start_task_id: int, target_task_id: int) -> bool:
    """Return whether a directed `blocks` path already connects two tasks."""
    if start_task_id == target_task_id:
        return True
    edges = db.execute(
        select(TaskDependency.source_task_id, TaskDependency.target_task_id).where(
            TaskDependency.link_type == "blocks"
        )
    ).all()
    graph = {}
    for source_id, target_id in edges:
        graph.setdefault(source_id, []).append(target_id)
    pending = [start_task_id]
    visited = set()
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        for neighbor in graph.get(current, ()):
            if neighbor == target_task_id:
                return True
            if neighbor not in visited:
                pending.append(neighbor)
    return False


def version(row, expected):
    if row.version != expected:
        fail(
            "Registro alterado por outra sessão. Atualize e tente novamente.",
            409,
            "CONFLICT",
        )


def get_column(db, key):
    return db.scalar(select(KanbanColumn).where(KanbanColumn.key == key))


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
    old_supplier = task.supplier_id
    task.supplier_id = identity
    audit(
        db,
        user,
        "task",
        task.id,
        "assignment_changed",
        supplier_id=identity,
        previous_supplier_id=old_supplier,
    )


def set_internal_assignee(db, actor, task, identity):
    active_internal_user(db, identity)
    if task.assignee_user_id == identity:
        return
    previous = task.assignee_user_id
    task.assignee_user_id = identity
    audit(
        db,
        actor,
        "task",
        task.id,
        "internal_assignee_changed",
        previous_user_id=previous,
        user_id=identity,
    )


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
            "work_type",
            "parent_id",
            "labels",
            "status",
            "resolution",
            "priority",
            "due",
            "planned_start",
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
    if user.role == "supplier" and task.parent_id:
        visible_parent = db.scalar(
            scoped_tasks(db, user).where(Task.id == task.parent_id)
        )
        if not visible_parent:
            result["parent_id"] = None
    if user.role != "supplier":
        result["assignee_user_id"] = task.assignee_user_id
    status_column = get_column(db, task.status)
    result["status_title"] = status_column.title if status_column else task.status
    result["release_ids"] = list(
        db.scalars(select(TaskRelease.release_id).where(TaskRelease.task_id == task.id))
    )
    result["component_ids"] = list(
        db.scalars(select(TaskComponent.component_id).where(TaskComponent.task_id == task.id))
    )
    if user.role != "supplier":
        result["links"] = [
            {
                "id": link.id,
                "task_id": link.target_task_id if link.source_task_id == task.id else link.source_task_id,
                "direction": "outgoing" if link.source_task_id == task.id else "incoming",
                "type": link.link_type,
            }
            for link in db.scalars(
                select(TaskDependency).where(
                    (TaskDependency.source_task_id == task.id)
                    | (TaskDependency.target_task_id == task.id)
                )
            )
        ]
    decision = db.scalar(
        select(Approval).where(Approval.task_id == task.id).order_by(Approval.id.desc())
    )
    result["approval_reason"] = decision.reason if decision and not decision.approved else ""
    current_hours = db.scalar(
        select(Hours).where(Hours.task_id == task.id, Hours.version == task.hours_version)
    ) if task.hours_version else None
    result["worklog_comment"] = current_hours.comment if current_hours else ""
    if user.role == "supplier" and current_hours and current_hours.author_id != user.id:
        result["worklog_comment"] = ""
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


def estimate_required(db, task, status):
    schema = current_schema(db, task)
    return bool(
        schema
        and any(
            field["type"] == "native"
            and field.get("native_key") == "estimated_minutes"
            and status in field["required_for"]
            for field in schema.fields
        )
    )


def move_task(db, user, task, data):
    version(task, data.version)
    columns = list(db.scalars(select(KanbanColumn).order_by(KanbanColumn.workflow_order)))
    statuses = [column.key for column in columns] or STATUSES
    columns_by_key = {column.key: column for column in columns}
    if data.status not in statuses:
        fail("Etapa inválida.")
    destination_is_done = data.status == "done" or (
        data.status in columns_by_key and columns_by_key[data.status].category == "done"
    )
    manager = user.role in {"admin", "manager"}
    supplier = supplier_for(db, user)
    if not manager and not (
        user.role == "supplier" and supplier and supplier.id == task.supplier_id
    ):
        fail("Sem autorização para mover esta atividade.", 403)
    origin = task.status
    resolution_before = task.resolution
    origin_is_done = origin == "done" or (
        origin in columns_by_key and columns_by_key[origin].category == "done"
    )
    configured = transition_policy(
        db.scalars(
            select(WorkflowTransition).where(
                WorkflowTransition.source == origin,
                WorkflowTransition.target == data.status,
            )
        ),
        task.work_type,
    )
    if configured:
        if not configured.enabled:
            fail("Esta transição está desativada no fluxo configurado.", 409)
        if configured.allowed_roles is not None and user.role not in configured.allowed_roles:
            fail("Seu perfil não pode executar esta transição.", 403)
    if not manager and (origin not in STATUSES or data.status not in STATUSES):
        fail("Somente gestor pode mover atividades em colunas adicionais.", 403)
    if data.status == origin:
        previous_priority = task.priority
        task.priority = data.priority
        task.version += 1
        audit(
            db,
            user,
            "task",
            task.id,
            "reordered",
            priority=data.priority,
            previous_priority=previous_priority,
        )
        return
    if configured and not conditions_match(configured.conditions, task, db):
        fail("As condições configuradas para esta transição não foram atendidas.", 409)
    if origin_is_done:
        reopen_target = "review" if origin == "done" else (task.board_origin_status or "review")
        default_reopen = data.status == reopen_target
        configured_reopen = configured is not None and configured.enabled
        if (
            not manager
            or destination_is_done
            or not (default_reopen or configured_reopen)
            or not data.reason
        ):
            fail(
                "Reabertura exige gestor, justificativa e retorno à revisão ou uma transição de reabertura configurada.",
                403,
            )
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
        task.board_origin_status = None
        task.resolution = None
    else:
        if origin in STATUSES and data.status in STATUSES:
            distance = STATUSES.index(data.status) - STATUSES.index(origin)
            if distance != 1 and not (distance < 0 and configured and configured.enabled):
                fail(
                    "Avanços devem seguir a próxima etapa; retornos exigem uma transição configurada."
                )
        elif origin in STATUSES and data.status not in STATUSES:
            if not manager:
                fail("Somente gestor pode mover atividades para colunas adicionais.", 403)
            if origin == "review" and task.approval != "approved":
                fail("Aguarde a aprovação ou corrija as horas antes de avançar.")
            task.board_origin_status = origin
        elif origin not in STATUSES and data.status not in STATUSES:
            if not manager:
                fail("Somente gestor pode reorganizar atividades em colunas adicionais.", 403)
        elif origin not in STATUSES and data.status in STATUSES:
            base_status = task.board_origin_status
            if not base_status or base_status not in STATUSES:
                fail("Etapa original da atividade adicional não foi encontrada.", 409)
            allowed_destinations = {base_status}
            if base_status != "done" and STATUSES.index(base_status) < len(STATUSES) - 1:
                allowed_destinations.add(STATUSES[STATUSES.index(base_status) + 1])
            if configured and configured.enabled:
                allowed_destinations.add(data.status)
            if data.status not in allowed_destinations:
                fail(
                    "Retorne à etapa de origem, avance para a próxima etapa ou configure esta transição."
                )
            task.board_origin_status = None
        if estimate_required(db, task, data.status) and task.estimated_minutes <= 0:
            fail("Preencha as horas previstas para mover esta atividade para Em produção.")
        if data.status == "review" and task.used_minutes <= 0:
            fail("Preencha as horas utilizadas para mover esta atividade para Em revisão.")
        if destination_is_done and (not manager or task.approval != "approved"):
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
        if configured and configured.required_fields:
            by_id = {field["id"]: field for field in schema.fields}
            extra_missing = [
                by_id[identity]["label"] if identity in by_id else identity
                for identity in configured.required_fields
                if identity not in by_id or (
                    field_value(task, schema, by_id[identity]) is None
                    or field_value(task, schema, by_id[identity]) == ""
                    or (
                        by_id[identity]["type"] == "checkbox"
                        and field_value(task, schema, by_id[identity]) is not True
                    )
                )
            ]
            if extra_missing:
                fail("Preencha os campos da transição: " + ", ".join(extra_missing))
    elif configured and configured.required_fields:
        fail("Configure os campos obrigatórios adicionais no card antes desta transição.")
    task.status, task.priority = data.status, data.priority
    if destination_is_done:
        task.resolution = data.resolution
    elif origin_is_done:
        task.resolution = None
    audit(
        db,
        user,
        "task",
        task.id,
        "status_changed",
        origin=origin,
        destination=data.status,
        reason=data.reason,
        resolution=task.resolution,
        changes=(
            [{"field": "resolution", "before": resolution_before, "after": task.resolution}]
            if resolution_before != task.resolution
            else []
        ),
    )
    if configured and configured.actions:
        apply_transition_actions(db, user, task, configured.actions, origin, data.status)


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
