import os
import secrets
import time
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone, date
from fastapi import FastAPI, Depends, Request, Response, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session as ORMSession
from sqlalchemy.orm.exc import StaleDataError
from argon2.exceptions import VerificationError, InvalidHashError
from .db import get_db
from .models import (
    User,
    Role,
    Session,
    Supplier,
    Rate,
    Task,
    Sprint,
    SprintTask,
    SchemaVersion,
    Hours,
    Approval,
    Audit,
)
from .security import (
    current_user,
    require,
    allowed,
    digest,
    hasher,
    supplier_for,
    PERMISSIONS,
)
from .schemas import (
    Login,
    UserInput,
    SupplierInput,
    SupplierCreate,
    RateInput,
    TaskCreate,
    TaskEdit,
    Move,
    HoursInput,
    Decision,
    SprintInput,
    SprintAction,
    AssignSprint,
    CardSchema,
    FieldValues,
    ReorderItem,
)
from .services import (
    fail,
    version,
    audit,
    scoped_tasks,
    get_task,
    task_payload,
    set_supplier,
    assignment,
    current_schema,
    estimate_required,
    validate_fields,
    validate_references,
    move_task,
    cost_cents,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
app = FastAPI(
    title="OS Manager",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc",
)
PREFIX = "/api/v1"
failures = defaultdict(list)


@app.exception_handler(RequestValidationError)
def invalid_input(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "INVALID_INPUT",
                "message": "Confira os campos enviados.",
                "fields": [".".join(map(str, error["loc"])) for error in exc.errors()],
            }
        },
    )


@app.exception_handler(StaleDataError)
def stale(request, exc):
    return JSONResponse(
        status_code=409,
        content={
            "detail": {
                "code": "CONFLICT",
                "message": "Registro alterado por outra sessão. Atualize a página.",
            }
        },
    )


@app.exception_handler(IntegrityError)
def integrity(request, exc):
    return JSONResponse(
        status_code=409,
        content={
            "detail": {
                "code": "CONFLICT",
                "message": "Operação viola um vínculo ou registro único.",
            }
        },
    )


@app.exception_handler(OperationalError)
def unavailable(request, exc):
    return JSONResponse(
        status_code=503,
        content={
            "detail": {
                "code": "DATABASE_UNAVAILABLE",
                "message": "Banco indisponível. Tente novamente.",
            }
        },
    )


@app.middleware("http")
async def request_security(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH"}:
        length = request.headers.get("content-length")
        if request.url.path.endswith("/attachments") and length is None:
            return JSONResponse(
                status_code=411,
                content={
                    "detail": {
                        "code": "LENGTH_REQUIRED",
                        "message": "Informe o tamanho do envio.",
                    }
                },
            )
        if length and (not length.isdigit() or int(length) > 6 * 1024 * 1024):
            return JSONResponse(
                status_code=413,
                content={
                    "detail": {
                        "code": "PAYLOAD_TOO_LARGE",
                        "message": "Envio excede o limite de 6 MiB.",
                    }
                },
            )
    origin = request.headers.get("origin")
    if (
        request.method not in {"GET", "HEAD", "OPTIONS"}
        and origin
        and origin.rstrip("/")
        not in {
            str(request.base_url).rstrip("/"),
            *os.getenv("TRUSTED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(","),
        }
    ):
        return JSONResponse(
            status_code=403,
            content={"detail": {"code": "ORIGIN", "message": "Origem não autorizada."}},
        )
    started = time.monotonic()
    response = await call_next(request)
    if response.status_code in {403, 404} and hasattr(request.state, "actor_id"):
        with ORMSession(request.state.db_bind) as audit_db:
            audit_db.add(
                Audit(
                    actor_id=request.state.actor_id,
                    entity="security",
                    entity_id=request.state.actor_id,
                    action="access_denied",
                    details={"method": request.method, "path": request.url.path},
                )
            )
            audit_db.commit()
    logging.getLogger("os_manager").info(
        json.dumps(
            {
                "event": "request",
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": int((time.monotonic() - started) * 1000),
            }
        )
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get(PREFIX + "/health")
def health(db=Depends(get_db)):
    db.execute(select(Role).limit(1))
    return {"status": "ok"}


@app.post(PREFIX + "/auth/login")
def login(data: Login, request: Request, response: Response, db=Depends(get_db)):
    key = (request.client.host, data.username.casefold())
    failures[key] = [instant for instant in failures[key] if instant > time.monotonic() - 300]
    if len(failures[key]) >= 10:
        fail("Muitas tentativas. Aguarde cinco minutos.", 429, "RATE_LIMIT")
    user = db.scalar(select(User).where(User.username == data.username))
    valid = False
    try:
        valid = hasher.verify(user.password_hash if user else DUMMY_HASH, data.password)
    except (VerificationError, InvalidHashError):
        pass
    if not valid or not user or not user.active:
        failures[key].append(time.monotonic())
        fail("Credenciais inválidas.", 401, "INVALID_CREDENTIALS")
    failures.pop(key, None)
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    db.add(
        Session(
            token_hash=digest(token),
            user_id=user.id,
            csrf=csrf,
            expires=(datetime.now(timezone.utc) + timedelta(hours=8)).isoformat(),
        )
    )
    db.commit()
    response.set_cookie(
        "session",
        token,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="strict",
        max_age=28800,
        path="/api",
    )
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "permissions": sorted(PERMISSIONS if user.role == "admin" else user.grants),
        "csrf": csrf,
    }


DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


@app.get(PREFIX + "/auth/me")
def me(request: Request, user=Depends(current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "permissions": sorted(PERMISSIONS if user.role == "admin" else user.grants),
        "csrf": request.state.session.csrf,
    }


@app.post(PREFIX + "/auth/logout")
def logout(request: Request, response: Response, user=Depends(current_user), db=Depends(get_db)):
    db.delete(request.state.session)
    db.commit()
    response.delete_cookie("session", path="/api")
    return {"ok": True}


@app.get(PREFIX + "/users")
def users(user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_users")
    return [
        {
            "id": row.id,
            "username": row.username,
            "role": row.role,
            "grants": row.grants,
            "active": row.active,
        }
        for row in db.scalars(select(User).order_by(User.id))
    ]


@app.get(PREFIX + "/permissions")
def permissions(user=Depends(current_user)):
    require(user, "manage_users")
    return sorted(PERMISSIONS)


@app.post(PREFIX + "/users", status_code=201)
def create_user(data: UserInput, user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_users")
    if (
        user.role != "admin"
        or data.role not in {"admin", "manager", "internal", "supplier"}
        or set(data.grants) - PERMISSIONS
    ):
        fail("Somente administrador pode atribuir acessos válidos.", 403)
    if data.role == "supplier" and data.grants:
        fail("Fornecedor não pode receber permissões internas.")
    row = User(
        username=data.username,
        password_hash=hasher.hash(data.password),
        role=data.role,
        grants=data.grants,
    )
    db.add(row)
    db.flush()
    audit(db, user, "user", row.id, "created", role=row.role, grants=row.grants)
    db.commit()
    return {"id": row.id}


@app.put(PREFIX + "/users/{identity}/grants")
def update_grants(identity: int, grants: list[str], user=Depends(current_user), db=Depends(get_db)):
    if user.role != "admin":
        fail("Somente administrador configura permissões.", 403)
    row = db.get(User, identity)
    if not row:
        fail("Usuário não encontrado.", 404)
    if set(grants) - PERMISSIONS or row.role == "supplier":
        fail("Permissões inválidas.")
    row.grants = grants
    audit(db, user, "user", row.id, "grants_changed", grants=grants)
    db.commit()
    return {"ok": True}


def supplier_payload(db, user, row):
    result = {
        "id": row.id,
        "name": row.name,
        "function": row.function,
        "active": row.active,
        "user_id": row.user_id,
    }
    if user.role in {"admin", "manager"} and allowed(user, "view_financial"):
        rate = db.scalar(select(Rate).where(Rate.supplier_id == row.id).order_by(Rate.id.desc()))
        result["rate_cents"] = rate.cents if rate else None
    return result


@app.get(PREFIX + "/suppliers")
def suppliers(
    q: str = "",
    active: bool | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    user=Depends(current_user),
    db=Depends(get_db),
):
    query = select(Supplier)
    if user.role == "supplier":
        query = query.where(Supplier.user_id == user.id)
    if q:
        query = query.where(Supplier.name.contains(q, autoescape=True))
    if active is not None:
        query = query.where(Supplier.active == active)
    return [
        supplier_payload(db, user, row)
        for row in db.scalars(query.order_by(Supplier.name).offset(offset).limit(limit))
    ]


@app.post(PREFIX + "/suppliers", status_code=201)
def create_supplier(data: SupplierCreate, user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_suppliers")
    if user.role not in {"admin", "manager"}:
        fail("Cadastro exige administrador ou gestor autorizado.", 403)
    if data.user_id:
        linked = db.get(User, data.user_id)
        if not linked or linked.role != "supplier":
            fail("Vínculo exige conta de fornecedor.")
    if data.active and data.initial_rate_cents is None:
        fail("Fornecedor ativo exige tarifa inicial.")
    if data.initial_rate_cents is not None:
        require(user, "change_rates")
    row = Supplier(**data.model_dump(exclude={"initial_rate_cents"}))
    db.add(row)
    db.flush()
    if data.initial_rate_cents is not None:
        db.add(
            Rate(
                supplier_id=row.id,
                cents=data.initial_rate_cents,
                author_id=user.id,
                reason="Tarifa inicial",
            )
        )
    audit(db, user, "supplier", row.id, "created")
    db.commit()
    return supplier_payload(db, user, row)


@app.put(PREFIX + "/suppliers/{identity}")
def edit_supplier(
    identity: int, data: SupplierInput, user=Depends(current_user), db=Depends(get_db)
):
    require(user, "manage_suppliers")
    if user.role not in {"admin", "manager"}:
        fail("Sem autorização.", 403)
    row = db.get(Supplier, identity)
    if not row:
        fail("Fornecedor não encontrado.", 404)
    if row.user_id != data.user_id:
        fail("Vínculo de login é imutável nesta versão. Cadastre o vínculo na criação.")
    if data.active and not db.scalar(select(Rate.id).where(Rate.supplier_id == identity).limit(1)):
        fail("Fornecedor ativo exige uma tarifa cadastrada.")
    previous = {"name": row.name, "function": row.function, "active": row.active}
    row.name, row.function, row.active = data.name, data.function, data.active
    audit(
        db,
        user,
        "supplier",
        row.id,
        "updated",
        before=previous,
        after={"name": row.name, "function": row.function, "active": row.active},
    )
    db.commit()
    return supplier_payload(db, user, row)


@app.post(PREFIX + "/suppliers/{identity}/rates", status_code=201)
def create_rate(identity: int, data: RateInput, user=Depends(current_user), db=Depends(get_db)):
    require(user, "change_rates")
    if user.role not in {"admin", "manager"}:
        fail("Sem autorização financeira.", 403)
    if not db.get(Supplier, identity):
        fail("Fornecedor não encontrado.", 404)
    row = Rate(supplier_id=identity, cents=data.cents, reason=data.reason, author_id=user.id)
    db.add(row)
    audit(db, user, "supplier", identity, "rate_created")
    db.commit()
    return {"id": row.id}


@app.get(PREFIX + "/suppliers/{identity}/rates")
def rate_history(identity: int, user=Depends(current_user), db=Depends(get_db)):
    require(user, "view_financial")
    if user.role not in {"admin", "manager"}:
        fail("Sem autorização financeira.", 403)
    return [
        {
            "id": row.id,
            "cents": row.cents,
            "created_at": row.created_at,
            "author_id": row.author_id,
            "reason": row.reason,
        }
        for row in db.scalars(
            select(Rate).where(Rate.supplier_id == identity).order_by(Rate.id.desc())
        )
    ]


from .repositories import filtered_tasks


@app.get(PREFIX + "/tasks")
def tasks(
    q: str = "",
    status: str | None = None,
    sprint_id: int | None = None,
    supplier_id: int | None = None,
    starts: date | None = None,
    ends: date | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    user=Depends(current_user),
    db=Depends(get_db),
):
    query = (
        filtered_tasks(db, user, q, status, sprint_id, supplier_id, starts, ends)
        .order_by(Task.priority, Task.id)
        .offset(offset)
        .limit(limit)
    )
    return [task_payload(db, user, row) for row in db.scalars(query)]


@app.get(PREFIX + "/tasks/{identity}")
def task_detail(identity: int, user=Depends(current_user), db=Depends(get_db)):
    return task_payload(db, user, get_task(db, user, identity))


@app.post(PREFIX + "/tasks", status_code=201)
def create_task(data: TaskCreate, user=Depends(current_user), db=Depends(get_db)):
    require(user, "create_tasks")
    row = Task(
        title=data.title,
        description=data.description,
        due=data.due.isoformat() if data.due else None,
        priority=data.priority,
        creator_id=user.id,
    )
    db.add(row)
    db.flush()
    set_supplier(db, user, row, data.supplier_id)
    if data.estimate_policy != "absent":
        db.add(
            SchemaVersion(
                task_id=row.id,
                version=1,
                author_id=user.id,
                values={},
                fields=[
                    {
                        "id": "native_estimated_minutes",
                        "label": "Horas previstas",
                        "type": "native",
                        "native_key": "estimated_minutes",
                        "options": [],
                        "required_for": ["production"]
                        if data.estimate_policy == "required"
                        else [],
                        "visible_to": ["admin", "manager", "internal", "supplier"],
                        "editable_by": ["supplier"],
                    }
                ],
            )
        )
    audit(db, user, "task", row.id, "created", estimate_policy=data.estimate_policy)
    db.commit()
    return task_payload(db, user, row)


@app.put(PREFIX + "/tasks/{identity}")
def update_task(identity: int, data: TaskEdit, user=Depends(current_user), db=Depends(get_db)):
    require(user, "create_tasks")
    row = get_task(db, user, identity, True)
    version(row, data.version)
    if row.status == "done":
        fail("Reabra a atividade antes de editar.", 409)
    set_supplier(db, user, row, data.supplier_id)
    row.title, row.description, row.priority = (
        data.title,
        data.description,
        data.priority,
    )
    row.due = data.due.isoformat() if data.due else None
    audit(db, user, "task", row.id, "edited")
    row.version += 1
    db.commit()
    return task_payload(db, user, row)


@app.post(PREFIX + "/tasks/{identity}/move")
def move(identity: int, data: Move, user=Depends(current_user), db=Depends(get_db)):
    row = get_task(db, user, identity, True)
    move_task(db, user, row, data)
    db.commit()
    return task_payload(db, user, row)


@app.put(PREFIX + "/tasks/{identity}/hours")
def put_hours(identity: int, data: HoursInput, user=Depends(current_user), db=Depends(get_db)):
    row = get_task(db, user, identity, True)
    version(row, data.version)
    supplier = supplier_for(db, user)
    if user.role != "supplier" or not supplier or supplier.id != row.supplier_id:
        fail("Somente fornecedor atribuído informa horas.", 403)
    if row.status == "done" or row.approval == "approved":
        fail("Horas aprovadas exigem reabertura formal.", 409)
    if (
        row.status == "production"
        and estimate_required(db, row, "production")
        and data.estimated_minutes <= 0
        or row.status == "review"
        and data.used_minutes <= 0
    ):
        fail("Horas positivas são obrigatórias nesta etapa.")
    if row.status in {"backlog", "todo"} and data.used_minutes:
        fail("Horas utilizadas são informadas durante produção ou revisão.")
    row.estimated_minutes, row.used_minutes = data.estimated_minutes, data.used_minutes
    row.hours_version += 1
    row.approval = "resubmitted" if row.approval == "rejected" else "pending"
    db.add(
        Hours(
            task_id=row.id,
            version=row.hours_version,
            estimated_minutes=row.estimated_minutes,
            used_minutes=row.used_minutes,
            author_id=user.id,
        )
    )
    audit(db, user, "task", row.id, "hours_submitted", hours_version=row.hours_version)
    db.commit()
    return task_payload(db, user, row)


@app.post(PREFIX + "/tasks/{identity}/approval")
def approve(identity: int, data: Decision, user=Depends(current_user), db=Depends(get_db)):
    require(user, "approve_hours")
    if user.role not in {"admin", "manager"}:
        fail("Aprovação exige gestor autorizado.", 403)
    row = get_task(db, user, identity, True)
    existing = db.scalar(
        select(Approval).where(
            Approval.task_id == identity, Approval.hours_version == data.hours_version
        )
    )
    if existing:
        if (
            existing.approved == data.approved
            and existing.reason == data.reason
            and row.hours_version == data.hours_version
        ):
            return task_payload(db, user, row)
        fail("Esta versão já recebeu uma decisão.", 409)
    version(row, data.version)
    submitted = db.scalar(
        select(Hours).where(Hours.task_id == identity, Hours.version == row.hours_version)
    )
    if (
        not submitted
        or row.status != "review"
        or row.used_minutes <= 0
        or row.hours_version != data.hours_version
    ):
        fail("Aprovação exige apontamento atual em revisão.", 409)
    if not data.approved and not data.reason:
        fail("Informe a justificativa da rejeição.")
    snapshot = assignment(db, row)
    if not snapshot:
        fail("Atividade sem alocação.")
    db.add(
        Approval(
            task_id=row.id,
            hours_version=row.hours_version,
            assignment_id=snapshot.id,
            sprint_id=row.sprint_id,
            approved=data.approved,
            used_minutes=row.used_minutes,
            author_id=user.id,
            reason=data.reason,
        )
    )
    row.approval = "approved" if data.approved else "rejected"
    audit(
        db,
        user,
        "task",
        row.id,
        "hours_decided",
        approved=data.approved,
        reason=data.reason,
        hours_version=row.hours_version,
    )
    db.commit()
    return task_payload(db, user, row)


@app.put(PREFIX + "/tasks/{identity}/schema")
def update_schema(identity: int, data: CardSchema, user=Depends(current_user), db=Depends(get_db)):
    if not (allowed(user, "configure_cards") or allowed(user, "create_tasks")):
        fail("Sem permissão para configurar cards.", 403)
    row = get_task(db, user, identity, True)
    version(row, data.version)
    if row.status == "done":
        fail("Reabra o card para editar.", 409)
    fields = [field.model_dump() for field in data.fields]
    previous = current_schema(db, row)
    values = dict(previous.values) if previous else {}
    previous_fields = {field["id"]: field for field in previous.fields} if previous else {}
    new_fields = {field["id"]: field for field in fields}
    for key, value in data.values.items():
        if previous and previous.values.get(key) == value:
            continue
        definition = previous_fields.get(key) or new_fields.get(key)
        if (
            not definition
            or user.role not in definition["editable_by"]
            or user.role not in definition["visible_to"]
        ):
            fail("Campo não disponível para edição.", 403)
    values.update(data.values)
    validate_fields(fields, values)
    validate_references(db, user, row, fields, values)
    if previous:
        for field in previous.fields:
            replacement = next((item for item in fields if item["id"] == field["id"]), None)
            if previous.values.get(field["id"]) not in (None, "") and (
                not replacement or replacement["type"] != field["type"]
            ):
                fail("Não remova nem altere o tipo de campo preenchido.")
    db.add(
        SchemaVersion(
            task_id=identity,
            version=(previous.version + 1 if previous else 1),
            fields=fields,
            values=values,
            author_id=user.id,
        )
    )
    row.version += 1
    audit(db, user, "task", identity, "schema_versioned")
    db.commit()
    return task_payload(db, user, row)


@app.put(PREFIX + "/tasks/{identity}/values")
def update_values(identity: int, data: FieldValues, user=Depends(current_user), db=Depends(get_db)):
    row = get_task(db, user, identity, True)
    version(row, data.version)
    previous = current_schema(db, row)
    if not previous or row.status == "done":
        fail("Card sem campos editáveis.")
    fields = {field["id"]: field for field in previous.fields}
    for key in data.values:
        if (
            key not in fields
            or user.role not in fields[key]["editable_by"]
            or user.role not in fields[key]["visible_to"]
        ):
            fail("Campo não disponível para edição.", 403)
    values = {**previous.values, **data.values}
    validate_fields(previous.fields, values)
    validate_references(db, user, row, previous.fields, values)
    db.add(
        SchemaVersion(
            task_id=identity,
            version=previous.version + 1,
            fields=previous.fields,
            values=values,
            author_id=user.id,
        )
    )
    row.version += 1
    audit(db, user, "task", identity, "values_versioned")
    db.commit()
    return task_payload(db, user, row)


@app.get(PREFIX + "/sprints")
def sprints(user=Depends(current_user), db=Depends(get_db)):
    query = select(Sprint).where(Sprint.archived.is_(False))
    if user.role == "supplier":
        query = query.where(Sprint.id.in_(scoped_tasks(db, user).with_only_columns(Task.sprint_id)))
    return [
        {
            "id": row.id,
            "name": row.name,
            "objective": row.objective,
            "starts": row.starts,
            "ends": row.ends,
            "state": row.state,
            "owner_id": row.owner_id,
            "version": row.version,
        }
        for row in db.scalars(query.order_by(Sprint.id.desc()))
    ]


@app.post(PREFIX + "/sprints", status_code=201)
def create_sprint(data: SprintInput, user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_sprints")
    if data.ends < data.starts:
        fail("Término deve ser posterior ou igual ao início.")
    row = Sprint(
        name=data.name,
        objective=data.objective,
        starts=data.starts.isoformat(),
        ends=data.ends.isoformat(),
        owner_id=user.id,
    )
    db.add(row)
    db.flush()
    audit(db, user, "sprint", row.id, "created")
    db.commit()
    return {"id": row.id}


@app.post(PREFIX + "/sprints/{identity}/tasks")
def include_task(identity: int, data: AssignSprint, user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_sprints")
    sprint = db.get(Sprint, identity)
    if not sprint or sprint.archived:
        fail("Sprint não encontrada.", 404)
    version(sprint, data.version)
    if sprint.state == "closed":
        fail("Sprint encerrada.", 409)
    task = get_task(db, user, data.task_id, True)
    version(task, data.task_version)
    if task.sprint_id or task.status != "backlog":
        fail("Atividade deve estar no backlog e sem sprint atual.", 409)
    task.sprint_id, task.status = identity, "todo"
    sprint.version += 1
    db.add(SprintTask(task_id=task.id, sprint_id=identity))
    audit(db, user, "task", task.id, "included_in_sprint", sprint_id=identity)
    db.commit()
    return task_payload(db, user, task)


@app.post(PREFIX + "/sprints/{identity}/action")
def sprint_action(
    identity: int, data: SprintAction, user=Depends(current_user), db=Depends(get_db)
):
    require(user, "manage_sprints")
    sprint = db.get(Sprint, identity)
    if not sprint or sprint.archived:
        fail("Sprint não encontrada.", 404)
    version(sprint, data.version)
    if data.action == "start" and sprint.state == "planned":
        sprint.state = "active"
    elif data.action == "close" and sprint.state == "active":
        sprint.state = "closed"
        for link in db.scalars(
            select(SprintTask).where(
                SprintTask.sprint_id == identity, SprintTask.active_key == "active"
            )
        ):
            task = db.get(Task, link.task_id)
            previous_snapshot = link.snapshot
            completed = db.scalar(
                select(Audit)
                .where(
                    Audit.entity == "task",
                    Audit.entity_id == task.id,
                    Audit.action == "status_changed",
                )
                .order_by(Audit.id.desc())
            )
            completed_at = (
                completed.created_at
                if completed and completed.details.get("destination") == "done"
                else None
            )
            schema = current_schema(db, task)
            link.snapshot = {
                "previous_closure": previous_snapshot,
                "title": task.title,
                "description": task.description,
                "due": task.due,
                "completed_at": completed_at,
                "schema_version_id": schema.id if schema else None,
                "status": task.status,
                "estimated_minutes": task.estimated_minutes,
                "used_minutes": task.used_minutes,
                "cost_cents": cost_cents(db, task, identity),
                "approval": task.approval,
                "hours_version": task.hours_version,
                "supplier_id": task.supplier_id,
            }
            link.final_status, link.active_key = task.status, None
            if task.status != "done":
                previous_status = task.status
                task.sprint_id, task.status = None, "backlog"
                audit(
                    db,
                    user,
                    "task",
                    task.id,
                    "returned_to_backlog",
                    sprint_id=identity,
                    previous_status=previous_status,
                )
    elif data.action == "reopen" and sprint.state == "closed":
        require(user, "reopen_sprints")
        if not data.reason:
            fail("Justifique a reabertura.")
        sprint.state = "active"
        for link in db.scalars(select(SprintTask).where(SprintTask.sprint_id == identity)):
            task = db.get(Task, link.task_id)
            if task.sprint_id == identity:
                link.active_key = "active"
    else:
        fail("Ação inválida para o estado da sprint.")
    audit(db, user, "sprint", identity, data.action, reason=data.reason)
    db.commit()
    return {"ok": True}


@app.get(PREFIX + "/audit")
def audit_history(entity: str, identity: int, user=Depends(current_user), db=Depends(get_db)):
    if user.role == "supplier":
        fail("Auditoria restrita a usuários internos.", 403)
    if entity == "task":
        if not db.get(Task, identity):
            fail("Atividade não encontrada.", 404)
    entries = db.scalars(
        select(Audit).where(Audit.entity == entity, Audit.entity_id == identity).order_by(Audit.id)
    )
    financial = user.role in {"admin", "manager"} and allowed(user, "view_financial")
    return [
        {
            "id": row.id,
            "actor_id": row.actor_id,
            "action": row.action,
            "created_at": row.created_at,
            "details": {
                key: value
                for key, value in row.details.items()
                if financial or "cost" not in key and "rate" not in key
            },
        }
        for row in entries
    ]


@app.get(PREFIX + "/dashboard")
def dashboard(
    status: str | None = None,
    sprint_id: int | None = None,
    supplier_id: int | None = None,
    starts: date | None = None,
    ends: date | None = None,
    user=Depends(current_user),
    db=Depends(get_db),
):
    from .reporting import records, indicators

    rows = records(db, user, status, sprint_id, supplier_id, starts, ends)
    result = indicators(db, rows)
    if user.role in {"admin", "manager"} and allowed(user, "view_financial"):
        result["cost_cents"] = sum(row["cost_cents"] for row in rows)
        result["by_supplier"] = [
            {
                "supplier_id": identity,
                "cost_cents": sum(
                    row["cost_cents"] for row in rows if row["supplier_id"] == identity
                ),
            }
            for identity in sorted(
                {row["supplier_id"] for row in rows if row["supplier_id"] is not None}
            )
        ]
    result["sprint_evolution"] = []
    visible = db.scalars(select(Sprint).order_by(Sprint.starts, Sprint.id))
    for sprint in visible:
        sprint_rows = records(db, user, status, sprint.id, supplier_id, starts, ends)
        if sprint_rows:
            summary = indicators(db, sprint_rows)
            result["sprint_evolution"].append(
                {
                    "name": sprint.name,
                    "planned": summary["planned"],
                    "done": summary["done"],
                    "completion_percent": summary["completion_percent"],
                }
            )
    return result


@app.get(PREFIX + "/exports/{format}")
def export(
    format: str,
    financial: bool = False,
    status: str | None = None,
    sprint_id: int | None = None,
    supplier_id: int | None = None,
    starts: date | None = None,
    ends: date | None = None,
    user=Depends(current_user),
    db=Depends(get_db),
):
    if user.role != "supplier":
        require(user, "export_data")
    if financial:
        require(user, "export_financial")
        require(user, "view_financial")
        if user.role not in {"admin", "manager"}:
            fail("Exportação financeira restrita.", 403)
    if format not in {"xlsx", "pdf"}:
        fail("Formato indisponível.", 404)
    from .reporting import records, indicators
    from .exports import build_export

    rows = records(db, user, status, sprint_id, supplier_id, starts, ends)
    filters = {
        "status": status,
        "sprint_id": sprint_id,
        "supplier_id": supplier_id,
        "starts": str(starts or ""),
        "ends": str(ends or ""),
    }
    buffer, media = build_export(format, rows, indicators(db, rows), financial, filters)
    audit(
        db,
        user,
        "export",
        user.id,
        "exported",
        format=format,
        financial=financial,
        count=len(rows),
    )
    db.commit()
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="os-manager.{format}"'},
    )


from .collaboration import router as collaboration_router

app.include_router(collaboration_router)


@app.put(PREFIX + "/sprints/{identity}")
def update_sprint(
    identity: int,
    data: SprintInput,
    expected_version: int,
    user=Depends(current_user),
    db=Depends(get_db),
):
    require(user, "manage_sprints")
    row = db.get(Sprint, identity)
    if not row or row.archived:
        fail("Sprint não encontrada.", 404)
    version(row, expected_version)
    if row.state != "planned":
        fail("Somente sprint planejada pode ter seus dados alterados.", 409)
    if data.ends < data.starts:
        fail("Período inválido.")
    row.name, row.objective, row.starts, row.ends = (
        data.name,
        data.objective,
        data.starts.isoformat(),
        data.ends.isoformat(),
    )
    audit(db, user, "sprint", identity, "edited")
    db.commit()
    return {"ok": True}


@app.delete(PREFIX + "/sprints/{identity}")
def archive_sprint(
    identity: int, expected_version: int, user=Depends(current_user), db=Depends(get_db)
):
    require(user, "manage_sprints")
    row = db.get(Sprint, identity)
    if not row:
        fail("Sprint não encontrada.", 404)
    version(row, expected_version)
    if row.state != "planned" or db.scalar(
        select(SprintTask.id).where(SprintTask.sprint_id == identity).limit(1)
    ):
        fail("Arquivamento exige sprint planejada e sem vínculos.", 409)
    row.archived = True
    audit(db, user, "sprint", identity, "archived")
    db.commit()
    return {"ok": True}


@app.delete(PREFIX + "/tasks/{identity}")
def archive_task(
    identity: int, expected_version: int, user=Depends(current_user), db=Depends(get_db)
):
    require(user, "create_tasks")
    row = get_task(db, user, identity, True)
    version(row, expected_version)
    if row.status != "backlog" or row.sprint_id or row.hours_version:
        fail(
            "Arquivamento exige atividade sem sprint e sem apontamentos no backlog.",
            409,
        )
    row.archived = True
    audit(db, user, "task", identity, "archived")
    db.commit()
    return {"ok": True}


@app.post(PREFIX + "/tasks/reorder")
def reorder(items: list[ReorderItem], user=Depends(current_user), db=Depends(get_db)):
    if not items or len(items) > 200 or len({item.id for item in items}) != len(items):
        fail("Lista de ordenação inválida.")
    rows = [get_task(db, user, item.id, True) for item in items]
    if user.role not in {"admin", "manager", "supplier"}:
        fail("Sem autorização para reordenar.", 403)
    if len({(row.sprint_id, row.status) for row in rows}) != 1:
        fail("Ordene somente cards da mesma etapa e sprint.")
    for row, item in zip(rows, items):
        version(row, item.version)
    positions = sorted(row.priority for row in rows)
    base = positions[0]
    for index, row in enumerate(rows):
        row.priority = base + index
        row.version += 1
        audit(db, user, "task", row.id, "reordered", priority=row.priority)
    db.commit()
    return {"ok": True}


@app.get(PREFIX + "/config")
def application_config(user=Depends(current_user)):
    from .settings import APP_TIMEZONE

    return {"timezone": APP_TIMEZONE, "locale": "pt-BR"}


@app.get(PREFIX + "/tasks/{identity}/schema")
def get_card_schema(identity: int, user=Depends(current_user), db=Depends(get_db)):
    if not (allowed(user, "create_tasks") or allowed(user, "configure_cards")):
        fail("Sem autorização para configurar cards.", 403)
    row = get_task(db, user, identity)
    schema = current_schema(db, row)
    return {"fields": schema.fields if schema else [], "version": schema.version if schema else 0}


@app.get(PREFIX + "/sprints/{identity}/history")
def sprint_history(identity: int, user=Depends(current_user), db=Depends(get_db)):
    sprint = db.get(Sprint, identity)
    if not sprint or sprint.archived:
        fail("Sprint não encontrada.", 404)
    from .reporting import records

    rows = records(db, user, sprint_id=identity)
    if user.role == "supplier" and not rows:
        fail("Sprint não encontrada.", 404)
    return rows
