import os
import asyncio
import secrets
import time
import json
import logging
from contextlib import asynccontextmanager
from uuid import uuid4
from collections import defaultdict
from datetime import datetime, timedelta, timezone, date
from fastapi import FastAPI, Depends, Request, Response, Query, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session as ORMSession
from sqlalchemy.orm.exc import StaleDataError
from argon2.exceptions import VerificationError, InvalidHashError
from .db import SessionLocal, get_db
from .email_notifications import deliver_due_email_notifications, smtp_settings
from .push_notifications import (
    deliver_due_push_notifications,
    encrypt_subscription,
    endpoint_hash,
    push_settings,
    validate_subscription_payload,
)
from .audit_trail import changes, field_changes, visible_details
from .automation import run_automations, run_due_scheduled_automations
from .filter_subscriptions import (
    initialize_matches,
    next_run,
    run_due_filter_subscriptions,
    subscription_payload,
    utc_now,
)
from .integrations import development_metadata, get_webhook_adapter, safe_url, task_ids
from .integration_events import record_development_event
from .query_language import apply_query
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
    KanbanColumn,
    KanbanSavedView,
    SavedFilter,
    Release,
    Component,
    TaskRelease,
    TaskComponent,
    TaskDependency,
    ResourceCapacity,
    WorkflowTransition,
    AutomationRule,
    Dashboard,
    DashboardWidget,
    DashboardWidgetPosition,
    FilterSubscription,
    DevelopmentEvent,
    CalendarFeedToken,
    UserGroup,
    UserGroupMembership,
    TaskWatcher,
    InAppNotification,
    NotificationPreference,
    PushSubscription,
)
from .security import (
    current_user,
    require,
    allowed,
    active_internal_user,
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
    KanbanColumnCreate,
    KanbanColumnRename,
    KanbanColumnOrder,
    SavedViewInput,
    SavedViewOrder,
    SavedFilterInput,
    TaskScheduleInput,
    ReleaseInput,
    ComponentInput,
    TaskLinkInput,
    CapacityInput,
    CapacityLevelingApply,
    CalendarExportInput,
    WorkflowTransitionInput,
    AutomationRuleInput,
    DashboardInput,
    DashboardWidgetInput,
    DashboardWidgetOrderInput,
    FilterSubscriptionInput,
    UserGroupInput,
    UserGroupMembersInput,
    NotificationPreferenceInput,
    PushSubscriptionInput,
)
from .services import (
    fail,
    version,
    audit,
    scoped_tasks,
    get_task,
    task_payload,
    set_supplier,
    set_internal_assignee,
    assignment,
    current_schema,
    estimate_required,
    validate_fields,
    validate_references,
    move_task,
    cost_cents,
    blocking_path_exists,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
async def automation_scheduler():
    while True:
        try:
            await asyncio.to_thread(run_due_scheduled_automations, SessionLocal)
        except Exception:
            logging.exception("Falha ao processar automações diárias.")
        try:
            await asyncio.to_thread(run_due_filter_subscriptions, SessionLocal)
        except Exception:
            logging.exception("Falha ao processar assinaturas de filtros.")
        try:
            await asyncio.to_thread(deliver_due_email_notifications, SessionLocal)
        except Exception:
            logging.exception("Falha ao processar notificações de e-mail.")
        try:
            await asyncio.to_thread(deliver_due_push_notifications, SessionLocal)
        except Exception:
            logging.exception("Falha ao processar notificações push.")
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(_app):
    scheduler_task = asyncio.create_task(automation_scheduler())
    try:
        yield
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Gestão de Demandas",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc",
    lifespan=lifespan,
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


def user_group_ids(db, user):
    if user.role == "supplier":
        return set()
    return set(
        db.scalars(
            select(UserGroupMembership.group_id)
            .join(UserGroup, UserGroup.id == UserGroupMembership.group_id)
            .where(UserGroupMembership.user_id == user.id, UserGroup.active.is_(True))
        )
    )


def shared_with_user(row, user, db):
    if user.role == "supplier" or not row.shared:
        return False
    return user.role in (row.shared_roles or []) or bool(
        user_group_ids(db, user).intersection(row.shared_group_ids or [])
    )


def validate_shared_groups(db, identity_list):
    if not identity_list:
        return
    active = set(
        db.scalars(
            select(UserGroup.id).where(UserGroup.id.in_(identity_list), UserGroup.active.is_(True))
        )
    )
    if active != set(identity_list):
        fail("Um ou mais grupos selecionados não estão disponíveis.")


@app.get(PREFIX + "/directory/groups")
def directory_groups(user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_planning")
    return [
        {"id": row.id, "name": row.name}
        for row in db.scalars(select(UserGroup).where(UserGroup.active.is_(True)).order_by(UserGroup.name))
    ]


@app.get(PREFIX + "/user-groups")
def list_user_groups(user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_users")
    rows = db.scalars(select(UserGroup).order_by(UserGroup.name))
    result = []
    for group in rows:
        members = db.execute(
            select(User.id, User.username, User.role)
            .join(UserGroupMembership, UserGroupMembership.user_id == User.id)
            .where(UserGroupMembership.group_id == group.id)
            .order_by(User.username)
        ).all()
        result.append(
            {
                "id": group.id,
                "name": group.name,
                "description": group.description,
                "active": group.active,
                "members": [{"id": row.id, "username": row.username, "role": row.role} for row in members],
            }
        )
    return result


@app.post(PREFIX + "/user-groups", status_code=201)
def create_user_group(data: UserGroupInput, user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_users")
    if user.role != "admin":
        fail("Somente administrador pode gerenciar grupos internos.", 403)
    if db.scalar(select(UserGroup.id).where(UserGroup.name == data.name)):
        fail("Já existe um grupo com esse nome.", 409)
    row = UserGroup(**data.model_dump(), author_id=user.id)
    db.add(row)
    db.flush()
    audit(db, user, "user_group", row.id, "created", name=row.name, active=row.active)
    db.commit()
    return {"id": row.id, "name": row.name, "description": row.description, "active": row.active, "members": []}


@app.put(PREFIX + "/user-groups/{identity}")
def update_user_group(identity: int, data: UserGroupInput, user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_users")
    if user.role != "admin":
        fail("Somente administrador pode gerenciar grupos internos.", 403)
    row = db.get(UserGroup, identity)
    if not row:
        fail("Grupo não encontrado.", 404)
    duplicate = db.scalar(select(UserGroup.id).where(UserGroup.name == data.name, UserGroup.id != identity))
    if duplicate:
        fail("Já existe um grupo com esse nome.", 409)
    before = {"name": row.name, "description": row.description, "active": row.active}
    row.name, row.description, row.active = data.name, data.description, data.active
    audit(db, user, "user_group", row.id, "updated", before=before, after=data.model_dump())
    db.commit()
    return {"id": row.id, **data.model_dump()}


@app.put(PREFIX + "/user-groups/{identity}/members")
def replace_user_group_members(
    identity: int, data: UserGroupMembersInput, user=Depends(current_user), db=Depends(get_db)
):
    require(user, "manage_users")
    if user.role != "admin":
        fail("Somente administrador pode gerenciar grupos internos.", 403)
    group = db.get(UserGroup, identity)
    if not group or not group.active:
        fail("Grupo não encontrado ou inativo.", 404)
    members = list(db.scalars(select(User).where(User.id.in_(data.user_ids)))) if data.user_ids else []
    if len(members) != len(data.user_ids) or any(member.role == "supplier" or not member.active for member in members):
        fail("Grupos internos aceitam somente contas internas ativas.")
    previous = list(
        db.scalars(select(UserGroupMembership.user_id).where(UserGroupMembership.group_id == identity))
    )
    db.query(UserGroupMembership).filter(UserGroupMembership.group_id == identity).delete(synchronize_session=False)
    db.add_all(
        UserGroupMembership(group_id=identity, user_id=member_id, author_id=user.id)
        for member_id in data.user_ids
    )
    audit(db, user, "user_group", identity, "members_replaced", previous_user_ids=previous, user_ids=data.user_ids)
    db.commit()
    return {"ok": True, "group_id": identity, "user_ids": data.user_ids}


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


def ical_escape(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def ical_fold(line: str) -> str:
    folded, current, byte_count = [], "", 0
    for character in line:
        size = len(character.encode("utf-8"))
        if byte_count + size > 73:
            folded.append(current)
            current, byte_count = " " + character, 1 + size
        else:
            current += character
            byte_count += size
    folded.append(current)
    return "\r\n".join(folded)


def _ical_timestamp(value: str | None) -> str:
    try:
        instant = datetime.fromisoformat(value or "")
    except ValueError:
        instant = datetime.now(timezone.utc)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _calendar_document(tasks, db):
    task_list = list(tasks)
    if not task_list:
        latest_audit = {}
    else:
        latest_audit = dict(
            db.execute(
                select(Audit.entity_id, func.max(Audit.created_at))
                .where(
                    Audit.entity == "task",
                    Audit.entity_id.in_([task.id for task in task_list]),
                )
                .group_by(Audit.entity_id)
            ).all()
        )
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Gestao de Demandas//Calendario//PT-BR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for task in task_list:
        if not task.due:
            continue
        due = date.fromisoformat(task.due)
        stamp = _ical_timestamp(latest_audit.get(task.id) or task.created_at)
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:os-{task.id}@gestao-de-demandas.local",
                f"DTSTAMP:{stamp}",
                f"LAST-MODIFIED:{stamp}",
                f"DTSTART;VALUE=DATE:{due.strftime('%Y%m%d')}",
                f"DTEND;VALUE=DATE:{(due + timedelta(days=1)).strftime('%Y%m%d')}",
                f"SUMMARY:{ical_escape(f'OS-{task.id} · {task.title}')}",
                f"STATUS:{'COMPLETED' if task.status == 'done' else 'CONFIRMED'}",
                "TRANSP:TRANSPARENT",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(ical_fold(line.rstrip()) for line in lines) + "\r\n"


@app.post(PREFIX + "/calendar.ics")
def export_calendar(
    data: CalendarExportInput,
    user=Depends(current_user),
    db=Depends(get_db),
):
    tasks_by_id = {
        task.id: task
        for task in db.scalars(
            scoped_tasks(db, user)
            .where(Task.id.in_(data.task_ids), Task.due.is_not(None))
            .order_by(Task.due, Task.id)
        )
    }
    ordered = [tasks_by_id[identity] for identity in data.task_ids if identity in tasks_by_id]
    content = _calendar_document(ordered, db)
    return Response(
        content,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="gestao-de-demandas.ics"'},
    )


@app.get(PREFIX + "/me/calendar-feed")
def calendar_feed_status(user=Depends(current_user), db=Depends(get_db)):
    row = db.get(CalendarFeedToken, user.id)
    return {"enabled": row is not None, "created_at": row.created_at if row else None}


@app.post(PREFIX + "/me/calendar-feed", status_code=201)
def create_calendar_feed(user=Depends(current_user), db=Depends(get_db)):
    token = secrets.token_urlsafe(48)
    row = db.get(CalendarFeedToken, user.id)
    action = "calendar_feed_created"
    now = datetime.now(timezone.utc).isoformat()
    if row:
        row.token_hash = digest(token)
        row.created_at = now
        action = "calendar_feed_rotated"
    else:
        db.add(CalendarFeedToken(user_id=user.id, token_hash=digest(token), created_at=now))
    audit(db, user, "user", user.id, action)
    db.commit()
    return {"token": token, "created_at": now}


@app.delete(PREFIX + "/me/calendar-feed")
def revoke_calendar_feed(user=Depends(current_user), db=Depends(get_db)):
    row = db.get(CalendarFeedToken, user.id)
    if row:
        db.delete(row)
        audit(db, user, "user", user.id, "calendar_feed_revoked")
        db.commit()
    return {"enabled": False}


calendar_basic_auth = HTTPBasic(auto_error=False)


def _calendar_auth_error():
    raise HTTPException(
        status_code=401,
        detail={"code": "UNAUTHENTICATED", "message": "Autenticação do feed de calendário inválida."},
        headers={"WWW-Authenticate": 'Basic realm="Calendar feed"'},
    )


def _calendar_bearer(credentials: HTTPBasicCredentials | None) -> str:
    if not credentials or credentials.username != "calendar" or not credentials.password:
        _calendar_auth_error()
    return credentials.password


@app.get(PREFIX + "/calendar/feed.ics")
def calendar_subscription_feed(
    credentials: HTTPBasicCredentials | None = Depends(calendar_basic_auth),
    db=Depends(get_db),
):
    token = _calendar_bearer(credentials)
    feed = db.scalar(
        select(CalendarFeedToken).where(CalendarFeedToken.token_hash == digest(token))
    )
    user = db.get(User, feed.user_id) if feed else None
    if not feed or not user or not user.active:
        _calendar_auth_error()
    tasks = list(
        db.scalars(
            scoped_tasks(db, user)
            .where(Task.due.is_not(None))
            .order_by(Task.due, Task.id)
        )
    )
    return Response(
        _calendar_document(tasks, db),
        media_type="text/calendar; charset=utf-8",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@app.get(PREFIX + "/tasks")
def tasks(
    q: str = "",
    jql: str = "",
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
    query = apply_query(
        filtered_tasks(db, user, q, status, sprint_id, supplier_id, starts, ends),
        jql,
        allow_configuration_history=user.role == "admin",
        actor_user_id=user.id,
        actor_role=user.role,
    )
    if not jql.strip() or "order by" not in jql.lower():
        query = query.order_by(Task.priority, Task.id)
    query = query.offset(offset).limit(limit)
    return [task_payload(db, user, row) for row in db.scalars(query)]


@app.get(PREFIX + "/tasks/{identity}")
def task_detail(identity: int, user=Depends(current_user), db=Depends(get_db)):
    return task_payload(db, user, get_task(db, user, identity))


@app.get(PREFIX + "/tasks/{identity}/watch")
def task_watch_state(identity: int, user=Depends(current_user), db=Depends(get_db)):
    get_task(db, user, identity)
    return {"watching": db.scalar(select(TaskWatcher.id).where(
        TaskWatcher.task_id == identity, TaskWatcher.user_id == user.id
    )) is not None}


@app.put(PREFIX + "/tasks/{identity}/watch")
def watch_task(identity: int, user=Depends(current_user), db=Depends(get_db)):
    get_task(db, user, identity)
    exists = db.scalar(select(TaskWatcher.id).where(
        TaskWatcher.task_id == identity, TaskWatcher.user_id == user.id
    ))
    if not exists:
        db.add(TaskWatcher(task_id=identity, user_id=user.id))
        audit(db, user, "task", identity, "watch_started")
        db.commit()
    return {"watching": True}


@app.delete(PREFIX + "/tasks/{identity}/watch")
def unwatch_task(identity: int, user=Depends(current_user), db=Depends(get_db)):
    get_task(db, user, identity)
    row = db.scalar(select(TaskWatcher).where(
        TaskWatcher.task_id == identity, TaskWatcher.user_id == user.id
    ))
    if row:
        db.delete(row)
        audit(db, user, "task", identity, "watch_stopped")
        db.commit()
    return {"watching": False}


@app.get(PREFIX + "/filter-subscriptions")
def list_filter_subscriptions(user=Depends(current_user), db=Depends(get_db)):
    rows = db.scalars(
        select(FilterSubscription)
        .where(FilterSubscription.user_id == user.id)
        .order_by(FilterSubscription.created_at.desc(), FilterSubscription.id.desc())
    )
    return [subscription_payload(db, row) for row in rows]


@app.post(PREFIX + "/filter-subscriptions", status_code=201)
def create_filter_subscription(
    data: FilterSubscriptionInput, user=Depends(current_user), db=Depends(get_db)
):
    current = utc_now()
    subscriptions = list(
        db.scalars(
            select(FilterSubscription.id)
            .where(FilterSubscription.user_id == user.id)
            .limit(20)
        )
    )
    if len(subscriptions) >= 20:
        fail("Cada conta pode manter até 20 assinaturas de filtro.", 422)
    if db.scalar(
        select(FilterSubscription.id).where(
            FilterSubscription.user_id == user.id,
            FilterSubscription.name == data.name,
        )
    ):
        fail("Já existe uma assinatura com esse nome nesta conta.", 409, "CONFLICT")

    row = FilterSubscription(
        user_id=user.id,
        name=data.name,
        query=data.query,
        frequency=data.frequency,
        active=data.active,
        next_run_at=next_run(data.frequency, current).isoformat(),
        last_run_at=current.isoformat(),
    )
    db.add(row)
    db.flush()
    initialize_matches(db, user, row)
    audit(db, user, "filter_subscription", row.id, "created", name=row.name)
    db.commit()
    return subscription_payload(db, row)


@app.put(PREFIX + "/filter-subscriptions/{identity}")
def update_filter_subscription(
    identity: int,
    data: FilterSubscriptionInput,
    user=Depends(current_user),
    db=Depends(get_db),
):
    row = db.scalar(
        select(FilterSubscription).where(
            FilterSubscription.id == identity,
            FilterSubscription.user_id == user.id,
        )
    )
    if not row:
        fail("Assinatura de filtro não encontrada.", 404)
    duplicate = db.scalar(
        select(FilterSubscription.id).where(
            FilterSubscription.user_id == user.id,
            FilterSubscription.name == data.name,
            FilterSubscription.id != identity,
        )
    )
    if duplicate:
        fail("Já existe uma assinatura com esse nome nesta conta.", 409, "CONFLICT")

    row.name = data.name
    row.query = data.query
    row.frequency = data.frequency
    row.active = data.active
    row.next_run_at = next_run(data.frequency, utc_now()).isoformat()
    row.last_run_at = utc_now().isoformat()
    row.last_error = ""
    initialize_matches(db, user, row)
    audit(db, user, "filter_subscription", row.id, "updated", name=row.name)
    db.commit()
    return subscription_payload(db, row)


@app.delete(PREFIX + "/filter-subscriptions/{identity}")
def delete_filter_subscription(identity: int, user=Depends(current_user), db=Depends(get_db)):
    row = db.scalar(
        select(FilterSubscription).where(
            FilterSubscription.id == identity,
            FilterSubscription.user_id == user.id,
        )
    )
    if not row:
        fail("Assinatura de filtro não encontrada.", 404)
    audit(db, user, "filter_subscription", row.id, "deleted", name=row.name)
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.get(PREFIX + "/notifications")
def notifications(
    unread_only: bool = False,
    limit: int = Query(30, ge=1, le=100),
    user=Depends(current_user),
    db=Depends(get_db),
):
    visible_ids = set(db.scalars(scoped_tasks(db, user).with_only_columns(Task.id)))
    query = select(InAppNotification).where(
        InAppNotification.user_id == user.id,
        InAppNotification.task_id.in_(visible_ids or {-1}),
    )
    if unread_only:
        query = query.where(InAppNotification.read_at.is_(None))
    rows = list(db.scalars(query.order_by(InAppNotification.created_at.desc(), InAppNotification.id.desc()).limit(limit)))
    task_ids_in_rows = {row.task_id for row in rows}
    tasks_by_id = {task.id: task for task in db.scalars(select(Task).where(Task.id.in_(task_ids_in_rows)))}
    actor_ids = {row.actor_id for row in rows if row.actor_id}
    actors = {actor.id: actor.username for actor in db.scalars(select(User).where(User.id.in_(actor_ids)))}
    return [
        {
            "id": row.id,
            "task_id": row.task_id,
            "task_title": tasks_by_id[row.task_id].title,
            "action": row.action,
            "source_label": row.source_label or None,
            "actor": actors.get(row.actor_id, "Sistema"),
            "created_at": row.created_at,
            "read": row.read_at is not None,
        }
        for row in rows
        if row.task_id in tasks_by_id
    ]


@app.put(PREFIX + "/notifications/{identity}/read")
def mark_notification_read(identity: int, user=Depends(current_user), db=Depends(get_db)):
    row = db.scalar(select(InAppNotification).where(
        InAppNotification.id == identity, InAppNotification.user_id == user.id
    ))
    if not row or not db.scalar(scoped_tasks(db, user).where(Task.id == row.task_id)):
        fail("Notificação não encontrada.", 404, "NOT_FOUND")
    if row.read_at is None:
        row.read_at = datetime.now(timezone.utc).isoformat()
        db.commit()
    return {"ok": True}


@app.get(PREFIX + "/me/notification-preferences")
def get_notification_preferences(user=Depends(current_user), db=Depends(get_db)):
    preference = db.get(NotificationPreference, user.id)
    return {
        "email": preference.email if preference else "",
        "email_enabled": preference.email_enabled if preference else False,
        "email_delivery_configured": smtp_settings() is not None,
    }


@app.put(PREFIX + "/me/notification-preferences")
def update_notification_preferences(
    data: NotificationPreferenceInput,
    user=Depends(current_user),
    db=Depends(get_db),
):
    if data.email_enabled and smtp_settings() is None:
        fail("O envio de e-mails não está configurado neste ambiente.", 503, "EMAIL_UNAVAILABLE")
    preference = db.get(NotificationPreference, user.id)
    if not preference:
        preference = NotificationPreference(user_id=user.id)
        db.add(preference)
    preference.email = data.email.lower() if data.email else None
    preference.email_enabled = data.email_enabled
    preference.updated_at = datetime.now(timezone.utc).isoformat()
    audit(
        db,
        user,
        "notification_preference",
        user.id,
        "updated",
        email_configured=bool(preference.email),
        email_enabled=preference.email_enabled,
    )
    db.commit()
    return get_notification_preferences(user, db)


@app.get(PREFIX + "/me/push-configuration")
def get_push_configuration(
    endpoint_identity: str | None = Query(default=None, pattern=r"^[0-9a-f]{64}$"),
    user=Depends(current_user),
    db=Depends(get_db),
):
    settings = push_settings()
    count = db.scalar(
        select(func.count()).select_from(PushSubscription).where(PushSubscription.user_id == user.id)
    ) or 0
    return {
        "available": settings is not None,
        "public_key": settings["public_key"] if settings else None,
        "device_count": count,
        "device_limit": 10,
        "active_on_this_browser": bool(
            endpoint_identity
            and db.scalar(
                select(PushSubscription.endpoint_hash).where(
                    PushSubscription.endpoint_hash == endpoint_identity,
                    PushSubscription.user_id == user.id,
                )
            )
        ),
    }


@app.post(PREFIX + "/me/push-subscriptions", status_code=201)
def register_push_subscription(
    data: PushSubscriptionInput,
    user=Depends(current_user),
    db=Depends(get_db),
):
    settings = push_settings()
    if not settings:
        fail("Notificações push não estão configuradas neste ambiente.", 503, "PUSH_UNAVAILABLE")
    payload = data.model_dump()
    if not validate_subscription_payload(payload):
        fail("Assinatura push inválida ou não suportada.", 422, "INVALID_PUSH_SUBSCRIPTION")
    identity = endpoint_hash(data.endpoint)
    row = db.get(PushSubscription, identity)
    if not row or row.user_id != user.id:
        count = db.scalar(
            select(func.count()).select_from(PushSubscription).where(PushSubscription.user_id == user.id)
        ) or 0
        if count >= 10:
            fail("Esta conta já possui o limite de 10 dispositivos push.", 409, "PUSH_DEVICE_LIMIT")
    if not row:
        row = PushSubscription(endpoint_hash=identity, user_id=user.id)
        db.add(row)
    row.user_id = user.id
    row.encrypted_payload = encrypt_subscription(payload, settings)
    audit(db, user, "user", user.id, "push_device_registered")
    db.commit()
    return {"ok": True, "device_count": db.scalar(
        select(func.count()).select_from(PushSubscription).where(PushSubscription.user_id == user.id)
    ) or 0}


@app.delete(PREFIX + "/me/push-subscriptions/{identity}")
def delete_push_subscription(identity: str, user=Depends(current_user), db=Depends(get_db)):
    if len(identity) != 64 or any(char not in "0123456789abcdef" for char in identity):
        fail("Dispositivo push não encontrado.", 404, "NOT_FOUND")
    row = db.scalar(
        select(PushSubscription).where(
            PushSubscription.endpoint_hash == identity,
            PushSubscription.user_id == user.id,
        )
    )
    if not row:
        fail("Dispositivo push não encontrado.", 404, "NOT_FOUND")
    db.delete(row)
    audit(db, user, "user", user.id, "push_device_removed")
    db.commit()
    count = db.scalar(
        select(func.count()).select_from(PushSubscription).where(PushSubscription.user_id == user.id)
    ) or 0
    return {"ok": True, "device_count": count}


@app.delete(PREFIX + "/me/push-subscriptions")
def delete_all_push_subscriptions(user=Depends(current_user), db=Depends(get_db)):
    rows = list(
        db.scalars(select(PushSubscription).where(PushSubscription.user_id == user.id))
    )
    for row in rows:
        db.delete(row)
    if rows:
        audit(db, user, "user", user.id, "push_devices_revoked", count=len(rows))
    db.commit()
    return {"ok": True, "device_count": 0}


@app.post(PREFIX + "/integrations/{provider}/webhook")
async def development_webhook(provider: str, request: Request, db=Depends(get_db)):
    adapter = get_webhook_adapter(provider)
    if not adapter:
        fail("Provedor de integração não suportado.", 404)
    body = await request.body()
    if len(body) > 1024 * 1024:
        fail("Webhook excede o limite de 1 MiB.", 413)
    valid = adapter.verify(os.getenv(adapter.secret_env, ""), body, request.headers)
    if not valid:
        fail("Assinatura de webhook inválida ou integração não configurada.", 403)
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        fail("Payload JSON inválido.")
    event_type, delivery_id = adapter.identify(request.headers)
    if not event_type or not delivery_id or len(delivery_id) > 160:
        fail("Webhook sem identificador de evento válido.")
    summary_text, event_url, actor, occurred = adapter.summarize(event_type, payload)
    event_metadata = development_metadata(provider, event_type, payload)
    identities = task_ids(payload)
    accepted = 0
    for identity in identities:
        task = db.get(Task, identity)
        if not task or task.archived:
            continue
        accepted += record_development_event(
            db,
            provider=provider,
            delivery_id=delivery_id,
            task=task,
            event_type=event_type,
            summary=summary_text,
            url=event_url,
            actor_name=actor,
            occurred_at=occurred,
            metadata=event_metadata,
        )
    db.commit()
    return {"received": True, "stored_events": accepted}


@app.get(PREFIX + "/tasks/{identity}/development")
def task_development_events(identity: int, user=Depends(current_user), db=Depends(get_db)):
    task = get_task(db, user, identity)
    return [
        {
            "id": row.id,
            "provider": row.provider,
            "event_type": row.event_type,
            "summary": row.summary,
            "url": safe_url(row.url),
            "actor": row.actor,
            "occurred_at": row.occurred_at,
            "received_at": row.received_at,
            "metadata": row.details or {},
        }
        for row in db.scalars(
            select(DevelopmentEvent)
            .where(DevelopmentEvent.task_id == task.id)
            .order_by(DevelopmentEvent.received_at.desc())
            .limit(100)
        )
    ]


def validate_parent(db, task, parent_id, work_type):
    allowed_parent_types = {
        "epic": set(),
        "story": {"epic"},
        "task": {"epic"},
        "bug": {"epic"},
        "subtask": {"story", "task", "bug"},
    }
    if work_type == "subtask" and parent_id is None:
        fail("Uma subtarefa precisa estar vinculada a um card pai.")
    if work_type == "epic" and parent_id is not None:
        fail("Um épico não pode ter card pai.")
    if task is not None and task.work_type != work_type:
        children = db.scalars(select(Task).where(Task.parent_id == task.id)).all()
        incompatible = [
            child
            for child in children
            if work_type not in allowed_parent_types[child.work_type]
        ]
        if incompatible:
            fail(
                "Não é possível alterar o tipo: existem cards filhos incompatíveis com a hierarquia resultante."
            )
    if parent_id is None:
        return
    if task is not None and parent_id == task.id:
        fail("Um card não pode ser pai de si mesmo.")
    parent = db.get(Task, parent_id)
    if not parent or parent.archived:
        fail("Card pai não encontrado.", 404)
    relationship_unchanged = (
        task is not None
        and task.parent_id == parent_id
        and task.work_type == work_type
    )
    if not relationship_unchanged and parent.work_type not in allowed_parent_types[work_type]:
        if work_type == "subtask":
            fail("Subtarefas devem ter como pai uma história, tarefa ou bug.")
        fail("Histórias, tarefas e bugs devem estar no nível raiz ou vinculados a um épico.")
    current = parent
    seen = {task.id} if task else set()
    while current:
        if current.id in seen:
            fail("A hierarquia não pode criar ciclos.")
        seen.add(current.id)
        current = db.get(Task, current.parent_id) if current.parent_id else None


def release_payload(row):
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "starts": row.starts,
        "due": row.due,
        "released_at": row.released_at,
        "archived": row.archived,
        "version": row.version,
    }


@app.get(PREFIX + "/releases")
def list_releases(user=Depends(current_user), db=Depends(get_db)):
    rows = list(
        db.scalars(
            select(Release).where(Release.archived.is_(False)).order_by(Release.due, Release.id)
        )
    )
    if user.role == "supplier":
        supplier = supplier_for(db, user)
        own_ids = set(
            db.scalars(select(Task.id).where(Task.supplier_id == (supplier.id if supplier else -1)))
        )
        linked = (
            set(db.scalars(select(TaskRelease.release_id).where(TaskRelease.task_id.in_(own_ids))))
            if own_ids
            else set()
        )
        rows = [row for row in rows if row.id in linked]
    return [release_payload(row) for row in rows]


@app.post(PREFIX + "/releases", status_code=201)
def create_release(data: ReleaseInput, user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_planning")
    row = Release(
        **data.model_dump(mode="json"),
        author_id=user.id,
    )
    db.add(row)
    db.flush()
    audit(db, user, "release", row.id, "created", name=row.name)
    db.commit()
    return release_payload(row)


@app.put(PREFIX + "/releases/{identity}")
def update_release(
    identity: int,
    data: ReleaseInput,
    expected_version: int = Query(gt=0),
    user=Depends(current_user),
    db=Depends(get_db),
):
    require(user, "manage_planning")
    row = db.get(Release, identity)
    if not row or row.archived:
        fail("Versão não encontrada.", 404)
    version(row, expected_version)
    if row.released_at:
        fail("Versão publicada é somente leitura.", 409)
    for key, value in data.model_dump(mode="json").items():
        setattr(row, key, value)
    row.version += 1
    audit(db, user, "release", row.id, "updated", name=row.name)
    db.commit()
    return release_payload(row)


@app.post(PREFIX + "/releases/{identity}/publish")
def publish_release(
    identity: int,
    expected_version: int = Query(gt=0),
    user=Depends(current_user),
    db=Depends(get_db),
):
    require(user, "manage_planning")
    row = db.get(Release, identity)
    if not row or row.archived:
        fail("Versão não encontrada.", 404)
    version(row, expected_version)
    if row.released_at:
        return release_payload(row)
    row.released_at = datetime.now(timezone.utc).isoformat()
    row.version += 1
    audit(db, user, "release", row.id, "published")
    db.commit()
    return release_payload(row)


@app.delete(PREFIX + "/releases/{identity}")
def archive_release(
    identity: int,
    expected_version: int = Query(gt=0),
    user=Depends(current_user),
    db=Depends(get_db),
):
    require(user, "manage_planning")
    row = db.get(Release, identity)
    if not row or row.archived:
        fail("Versão não encontrada.", 404)
    version(row, expected_version)
    row.archived = True
    row.version += 1
    audit(db, user, "release", row.id, "archived")
    db.commit()
    return {"ok": True}


@app.get(PREFIX + "/components")
def list_components(user=Depends(current_user), db=Depends(get_db)):
    rows = list(
        db.scalars(select(Component).where(Component.active.is_(True)).order_by(Component.name))
    )
    if user.role == "supplier":
        supplier = supplier_for(db, user)
        own_ids = set(
            db.scalars(select(Task.id).where(Task.supplier_id == (supplier.id if supplier else -1)))
        )
        linked = (
            set(
                db.scalars(
                    select(TaskComponent.component_id).where(TaskComponent.task_id.in_(own_ids))
                )
            )
            if own_ids
            else set()
        )
        rows = [row for row in rows if row.id in linked]
    return [
        {
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "owner_id": row.owner_id,
            "active": row.active,
        }
        for row in rows
    ]


@app.post(PREFIX + "/components", status_code=201)
def create_component(data: ComponentInput, user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_planning")
    if data.owner_id and not db.get(User, data.owner_id):
        fail("Responsável não encontrado.")
    row = Component(**data.model_dump(), author_id=user.id)
    db.add(row)
    db.flush()
    audit(db, user, "component", row.id, "created", name=row.name)
    db.commit()
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "owner_id": row.owner_id,
        "active": row.active,
    }


@app.put(PREFIX + "/components/{identity}")
def update_component(
    identity: int, data: ComponentInput, user=Depends(current_user), db=Depends(get_db)
):
    require(user, "manage_planning")
    row = db.get(Component, identity)
    if not row:
        fail("Componente não encontrado.", 404)
    if data.owner_id and not db.get(User, data.owner_id):
        fail("Responsável não encontrado.")
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    audit(db, user, "component", row.id, "updated", name=row.name, active=row.active)
    db.commit()
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "owner_id": row.owner_id,
        "active": row.active,
    }


@app.put(PREFIX + "/tasks/{identity}/planning-links")
def update_task_planning_links(
    identity: int,
    releases: list[int] = Query(default=[]),
    components: list[int] = Query(default=[]),
    user=Depends(current_user),
    db=Depends(get_db),
):
    require(user, "manage_planning")
    task = get_task(db, user, identity, True)
    if (
        len(releases) > 20
        or len(set(releases)) != len(releases)
        or len(components) > 20
        or len(set(components)) != len(components)
    ):
        fail("Lista de versões ou componentes inválida.")
    if any(not (row := db.get(Release, release_id)) or row.archived for release_id in releases):
        fail("Uma versão selecionada está indisponível.")
    if any(
        not (row := db.get(Component, component_id)) or not row.active
        for component_id in components
    ):
        fail("Um componente selecionado está indisponível.")
    db.query(TaskRelease).filter(TaskRelease.task_id == task.id).delete(synchronize_session=False)
    db.query(TaskComponent).filter(TaskComponent.task_id == task.id).delete(
        synchronize_session=False
    )
    for release_id in releases:
        db.add(TaskRelease(task_id=task.id, release_id=release_id, author_id=user.id))
    for component_id in components:
        db.add(TaskComponent(task_id=task.id, component_id=component_id, author_id=user.id))
    task.version += 1
    audit(
        db,
        user,
        "task",
        task.id,
        "planning_links_changed",
        releases=releases,
        components=components,
    )
    db.commit()
    return task_payload(db, user, task)


@app.post(PREFIX + "/tasks/{identity}/links", status_code=201)
def create_task_link(
    identity: int, data: TaskLinkInput, user=Depends(current_user), db=Depends(get_db)
):
    require(user, "manage_planning")
    source = get_task(db, user, identity, True)
    target = get_task(db, user, data.target_task_id, True)
    if data.link_type == "blocks" and blocking_path_exists(db, target.id, source.id):
        fail(
            "Essa dependência criaria um ciclo de bloqueio. Ajuste a direção das relações.",
            409,
            "DEPENDENCY_CYCLE",
        )
    link = TaskDependency(
        source_task_id=source.id,
        target_task_id=target.id,
        link_type=data.link_type,
        author_id=user.id,
    )
    db.add(link)
    db.flush()
    audit(
        db,
        user,
        "task",
        source.id,
        "dependency_added",
        target_task_id=target.id,
        link_type=data.link_type,
    )
    run_automations(
        db,
        user,
        source,
        "link_added",
        event_context={"link_type": link.link_type, "target_task_id": target.id},
    )
    db.commit()
    return {
        "id": link.id,
        "source_task_id": source.id,
        "target_task_id": target.id,
        "link_type": link.link_type,
    }


@app.delete(PREFIX + "/tasks/{identity}/links/{link_id}")
def delete_task_link(identity: int, link_id: int, user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_planning")
    task = get_task(db, user, identity, True)
    link = db.get(TaskDependency, link_id)
    if not link or task.id not in {link.source_task_id, link.target_task_id}:
        fail("Relação não encontrada.", 404)
    target_id = link.target_task_id if link.source_task_id == task.id else link.source_task_id
    audit(db, user, "task", task.id, "dependency_removed", link_id=link.id)
    db.delete(link)
    db.flush()
    run_automations(
        db,
        user,
        task,
        "link_removed",
        event_context={"link_type": link.link_type, "target_task_id": target_id},
    )
    db.commit()
    return {"ok": True}


@app.get(PREFIX + "/capacity")
def list_capacity(
    starts: date | None = None,
    ends: date | None = None,
    user=Depends(current_user),
    db=Depends(get_db),
):
    require(user, "manage_capacity")
    query = select(ResourceCapacity)
    if starts:
        query = query.where(ResourceCapacity.ends >= starts.isoformat())
    if ends:
        query = query.where(ResourceCapacity.starts <= ends.isoformat())
    return [
        capacity_payload(db, row)
        for row in db.scalars(query.order_by(ResourceCapacity.starts, ResourceCapacity.id))
    ]


def capacity_payload(db, row, *, include_internal=False):
    from .capacity_leveling import apply_capacity_moves, recommend_capacity_moves

    def period_days(start: date, end: date) -> list[date]:
        days = []
        current = start
        while current <= end:
            days.append(current)
            current += timedelta(days=1)
        weekdays = [day for day in days if day.weekday() < 5]
        return weekdays or days

    def distribute(minutes: int, days: list[date]) -> dict[date, int]:
        if not days:
            return {}
        quotient, remainder = divmod(max(0, minutes), len(days))
        return {day: quotient + (index < remainder) for index, day in enumerate(days)}

    capacity_start = date.fromisoformat(row.starts)
    capacity_end = date.fromisoformat(row.ends)
    capacity_days = period_days(capacity_start, capacity_end)
    daily_capacity = distribute(row.minutes, capacity_days)
    group = db.get(UserGroup, row.group_id) if row.group_id is not None else None
    if row.user_id is not None:
        task_query = select(Task).where(Task.assignee_user_id == row.user_id)
    elif row.group_id is not None:
        task_query = select(Task).where(
            Task.assignee_user_id.in_(row.group_member_ids or [])
        )
    else:
        task_query = select(Task).where(Task.supplier_id == row.supplier_id)
    tasks = list(
        db.scalars(task_query.where(Task.archived.is_(False), Task.status != "done"))
    )
    included, unplanned = 0, 0
    task_allocations = []
    for task in tasks:
        task_start = task.planned_start or task.due
        task_end = task.due or task.planned_start
        if not task_start or not task_end:
            unplanned += 1
            continue
        if task_start <= row.ends and task_end >= row.starts:
            included += 1
            planned_days = period_days(date.fromisoformat(task_start), date.fromisoformat(task_end))
            task_distribution = distribute(task.estimated_minutes, planned_days)
            allocated_days = {}
            for day in capacity_days:
                allocated = task_distribution.get(day, 0)
                if allocated:
                    allocated_days[day.isoformat()] = allocated
            if allocated_days:
                task_allocations.append(
                    {
                        "task_id": task.id,
                        "title": task.title,
                        "due": task_end,
                        "days": [day.isoformat() for day in planned_days if day in capacity_days],
                        "daily": allocated_days,
                        "source": {
                            "version": task.version,
                            "estimated_minutes": task.estimated_minutes,
                            "planned_start": task_start,
                            "due": task_end,
                        },
                    }
                )
    source_snapshot = {
        str(allocation["task_id"]): allocation["source"]
        for allocation in task_allocations
    }
    capacity_snapshot = {
        "supplier_id": row.supplier_id,
        "user_id": row.user_id,
        "group_id": row.group_id,
        "group_member_ids": list(row.group_member_ids or []),
        "starts": row.starts,
        "ends": row.ends,
        "minutes": row.minutes,
    }
    plan_history = row.leveling_plans or []
    latest_plan = plan_history[-1] if plan_history else None
    plan_stale = False
    current_shifts = []
    plan_active = False
    if latest_plan:
        plan_stale = (
            latest_plan.get("capacity") != capacity_snapshot
            or latest_plan.get("source") != source_snapshot
        )
        if not plan_stale:
            try:
                apply_capacity_moves(task_allocations, latest_plan.get("shifts", []))
                current_shifts = list(latest_plan.get("shifts", []))
                plan_active = True
            except (TypeError, ValueError, KeyError):
                plan_stale = True

    daily_demand = {day: 0 for day in capacity_days}
    daily_tasks = {day: 0 for day in capacity_days}
    for allocation in task_allocations:
        for day_key, minutes in allocation["daily"].items():
            day = date.fromisoformat(day_key)
            if day in daily_demand and minutes > 0:
                daily_demand[day] += minutes
                daily_tasks[day] += 1
    leveled_demand, suggested_shifts = recommend_capacity_moves(
        {day.isoformat(): minutes for day, minutes in daily_capacity.items()},
        {day.isoformat(): minutes for day, minutes in daily_demand.items()},
        task_allocations,
    )
    daily = [
        {
            "date": day.isoformat(),
            "demand_minutes": daily_demand[day],
            "suggested_demand_minutes": leveled_demand[day.isoformat()],
            "capacity_minutes": daily_capacity[day],
            "task_count": daily_tasks[day],
            "overload_minutes": max(0, daily_demand[day] - daily_capacity[day]),
            "suggested_overload_minutes": max(
                0, leveled_demand[day.isoformat()] - daily_capacity[day]
            ),
        }
        for day in capacity_days
    ]
    demand = sum(daily_demand.values())
    payload = {
        "id": row.id,
        "supplier_id": row.supplier_id,
        "user_id": row.user_id,
        "group_id": row.group_id,
        "group_name": group.name if group else None,
        "group_member_count": len(row.group_member_ids or []) if row.group_id is not None else None,
        "starts": row.starts,
        "ends": row.ends,
        "minutes": row.minutes,
        "notes": row.notes,
        "demand_minutes": demand,
        "demand_tasks": included,
        "unplanned_tasks": unplanned,
        "daily": daily,
        "utilization_percent": round(demand * 100 / row.minutes, 1) if row.minutes else None,
        "overload_minutes": sum(day["overload_minutes"] for day in daily),
        "suggested_overload_minutes": sum(day["suggested_overload_minutes"] for day in daily),
        "levelable_minutes": sum(item["minutes"] for item in suggested_shifts),
        "suggested_shift_count": len(suggested_shifts),
        "suggested_shifts": suggested_shifts[:50],
        "leveling_plan_version": row.leveling_plan_version,
        "leveling_plan_active": plan_active,
        "leveling_plan_stale": plan_stale,
        "leveling_plan_applied_at": latest_plan.get("created_at") if plan_active else None,
        "_leveling": {
            "capacity": capacity_snapshot,
            "source": source_snapshot,
            "previous_shifts": current_shifts,
            "suggested_shifts": suggested_shifts,
        },
    }
    if not include_internal:
        payload.pop("_leveling")
    return payload


@app.post(PREFIX + "/capacity/{identity}/level")
def apply_capacity_leveling(
    identity: int,
    data: CapacityLevelingApply,
    user=Depends(current_user),
    db=Depends(get_db),
):
    require(user, "manage_capacity")
    row = db.get(ResourceCapacity, identity)
    if not row:
        fail("Capacidade não encontrada.", 404)
    current = capacity_payload(db, row, include_internal=True)
    if data.expected_plan_version != current["leveling_plan_version"]:
        fail("A previsão de capacidade foi alterada. Atualize e tente novamente.", 409, "CONFLICT")
    leveling = current["_leveling"]
    additions = leveling["suggested_shifts"]
    if not additions:
        fail("Não há recomendações aplicáveis nesta previsão.", 409, "NO_LEVELING_MOVES")
    claimed = db.execute(
        update(ResourceCapacity)
        .where(
            ResourceCapacity.id == row.id,
            ResourceCapacity.leveling_plan_version == data.expected_plan_version,
        )
        .values(leveling_plan_version=data.expected_plan_version + 1)
    )
    if claimed.rowcount != 1:
        fail("A previsão de capacidade foi alterada. Atualize e tente novamente.", 409, "CONFLICT")
    row.leveling_plan_version = data.expected_plan_version + 1
    plan = {
        "version": row.leveling_plan_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "author_id": user.id,
        "capacity": leveling["capacity"],
        "source": leveling["source"],
        "shifts": [*leveling["previous_shifts"], *additions],
        "shift_count": len(leveling["previous_shifts"]) + len(additions),
        "shifted_minutes": sum(
            item["minutes"] for item in [*leveling["previous_shifts"], *additions]
        ),
    }
    row.leveling_plans = [*(row.leveling_plans or []), plan]
    audit(
        db,
        user,
        "capacity",
        row.id,
        "leveling_applied",
        plan_snapshot=plan,
        previous_version=current["leveling_plan_version"],
    )
    db.commit()
    return capacity_payload(db, row)


def validate_capacity_overlap(db, data, exclude_id=None):
    resource_filter = (
        ResourceCapacity.user_id == data.user_id
        if data.user_id is not None
        else ResourceCapacity.group_id == data.group_id
        if data.group_id is not None
        else ResourceCapacity.supplier_id == data.supplier_id
    )
    query = select(ResourceCapacity.id).where(
        resource_filter,
        ResourceCapacity.starts <= data.ends.isoformat(),
        ResourceCapacity.ends >= data.starts.isoformat(),
    )
    if exclude_id is not None:
        query = query.where(ResourceCapacity.id != exclude_id)
    if db.scalar(query.limit(1)):
        fail("Já existe capacidade cadastrada para esse recurso em um período sobreposto.", 409)


@app.get(PREFIX + "/directory/users")
def capacity_user_directory(user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_capacity")
    return [
        {"id": row.id, "username": row.username, "role": row.role}
        for row in db.scalars(
            select(User)
            .where(User.active.is_(True), User.role != "supplier")
            .order_by(User.username)
            .limit(500)
        )
    ]


@app.get(PREFIX + "/capacity/groups")
def capacity_group_directory(user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_capacity")
    groups = []
    for group in db.scalars(
        select(UserGroup).where(UserGroup.active.is_(True)).order_by(UserGroup.name, UserGroup.id)
    ):
        member_ids = list(
            db.scalars(
                select(UserGroupMembership.user_id)
                .join(User, User.id == UserGroupMembership.user_id)
                .where(
                    UserGroupMembership.group_id == group.id,
                    User.active.is_(True),
                    User.role != "supplier",
                )
                .order_by(UserGroupMembership.user_id)
            )
        )
        if member_ids:
            groups.append({"id": group.id, "name": group.name, "member_count": len(member_ids)})
    return groups


def capacity_group_member_snapshot(db, group_id):
    group = db.get(UserGroup, group_id)
    if not group or not group.active:
        fail("Equipe indisponível para planejamento de capacidade.")
    member_ids = list(
        db.scalars(
            select(UserGroupMembership.user_id)
            .join(User, User.id == UserGroupMembership.user_id)
            .where(
                UserGroupMembership.group_id == group_id,
                User.active.is_(True),
                User.role != "supplier",
            )
            .order_by(UserGroupMembership.user_id)
        )
    )
    if not member_ids:
        fail("Adicione ao menos uma pessoa interna ativa à equipe.")
    return member_ids


@app.get(PREFIX + "/directory/assignees")
def task_assignee_directory(user=Depends(current_user), db=Depends(get_db)):
    require(user, "create_tasks")
    return [
        {"id": row.id, "username": row.username, "role": row.role}
        for row in db.scalars(
            select(User)
            .where(User.active.is_(True), User.role != "supplier")
            .order_by(User.username)
            .limit(500)
        )
    ]


@app.get(PREFIX + "/directory/workflow-assignees")
def workflow_assignee_directory(user=Depends(current_user), db=Depends(get_db)):
    if not (allowed(user, "manage_workflows") or allowed(user, "manage_automation")):
        fail("Permissão insuficiente.", 403, "FORBIDDEN")
    return [
        {"id": row.id, "username": row.username, "role": row.role}
        for row in db.scalars(
            select(User)
            .where(User.active.is_(True), User.role != "supplier")
            .order_by(User.username)
            .limit(500)
        )
    ]


@app.post(PREFIX + "/capacity", status_code=201)
def create_capacity(data: CapacityInput, user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_capacity")
    if data.supplier_id and not db.get(Supplier, data.supplier_id):
        fail("Fornecedor não encontrado.")
    if data.user_id and not db.get(User, data.user_id):
        fail("Usuário não encontrado.")
    group_member_ids = capacity_group_member_snapshot(db, data.group_id) if data.group_id else []
    validate_capacity_overlap(db, data)
    row = ResourceCapacity(
        **data.model_dump(mode="json"),
        group_member_ids=group_member_ids,
        author_id=user.id,
    )
    db.add(row)
    db.flush()
    audit(
        db,
        user,
        "capacity",
        row.id,
        "created",
        starts=row.starts,
        ends=row.ends,
        minutes=row.minutes,
        supplier_id=row.supplier_id,
        user_id=row.user_id,
        group_id=row.group_id,
        group_member_count=len(group_member_ids),
    )
    db.commit()
    return capacity_payload(db, row)


@app.put(PREFIX + "/capacity/{identity}")
def update_capacity(
    identity: int, data: CapacityInput, user=Depends(current_user), db=Depends(get_db)
):
    require(user, "manage_capacity")
    row = db.get(ResourceCapacity, identity)
    if not row:
        fail("Capacidade não encontrada.", 404)
    if data.supplier_id and not db.get(Supplier, data.supplier_id):
        fail("Fornecedor não encontrado.")
    if data.user_id and not db.get(User, data.user_id):
        fail("Usuário não encontrado.")
    group_member_ids = capacity_group_member_snapshot(db, data.group_id) if data.group_id else []
    validate_capacity_overlap(db, data, identity)
    for key, value in data.model_dump(mode="json").items():
        setattr(row, key, value)
    row.group_member_ids = group_member_ids
    audit(
        db,
        user,
        "capacity",
        row.id,
        "updated",
        starts=row.starts,
        ends=row.ends,
        minutes=row.minutes,
        group_id=row.group_id,
        group_member_count=len(group_member_ids),
    )
    db.commit()
    return capacity_payload(db, row)


@app.delete(PREFIX + "/capacity/{identity}")
def delete_capacity(identity: int, user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_capacity")
    row = db.get(ResourceCapacity, identity)
    if not row:
        fail("Capacidade não encontrada.", 404)
    audit(db, user, "capacity", row.id, "deleted", starts=row.starts, ends=row.ends)
    db.delete(row)
    db.commit()
    return {"ok": True}


def workflow_payload(row):
    return {
        "id": row.id,
        "source": row.source,
        "target": row.target,
        "enabled": row.enabled,
        "roles": row.roles,
        "work_types": row.work_types or [],
        "type_rules": row.type_rules or {},
        "required_fields": row.required_fields,
        "conditions": row.conditions or [],
        "actions": row.actions or [],
    }


def validate_workflow_assignees(db, data):
    for condition in data.conditions:
        if condition.field == "assignee":
            active_internal_user(db, condition.value)
    for configured in data.actions:
        if configured.action in {"assign_internal_user", "add_watcher"}:
            active_internal_user(db, configured.config["user_id"])
    for policy in data.type_rules.values():
        for condition in policy.conditions:
            if condition.field == "assignee":
                active_internal_user(db, condition.value)
        for configured in policy.actions:
            if configured.action in {"assign_internal_user", "add_watcher"}:
                active_internal_user(db, configured.config["user_id"])


@app.get(PREFIX + "/workflows/transitions")
def list_workflow_transitions(user=Depends(current_user), db=Depends(get_db)):
    return [
        workflow_payload(row)
        for row in db.scalars(
            select(WorkflowTransition).order_by(
                WorkflowTransition.source, WorkflowTransition.target
            )
        )
    ]


@app.post(PREFIX + "/workflows/transitions", status_code=201)
def create_workflow_transition(
    data: WorkflowTransitionInput, user=Depends(current_user), db=Depends(get_db)
):
    require(user, "manage_workflows")
    validate_workflow_assignees(db, data)
    statuses = {row.key for row in db.scalars(select(KanbanColumn))}
    if data.source not in statuses or data.target not in statuses or data.source == data.target:
        fail("Selecione duas etapas diferentes do quadro.")
    row = WorkflowTransition(**data.model_dump(), author_id=user.id)
    db.add(row)
    db.flush()
    audit(
        db,
        user,
        "workflow",
        row.id,
        "transition_configured",
        source=row.source,
        target=row.target,
        enabled=row.enabled,
        work_types=row.work_types or [],
        type_rules=row.type_rules or {},
        conditions=row.conditions or [],
        actions=row.actions or [],
    )
    db.commit()
    return workflow_payload(row)


@app.put(PREFIX + "/workflows/transitions/{identity}")
def update_workflow_transition(
    identity: int, data: WorkflowTransitionInput, user=Depends(current_user), db=Depends(get_db)
):
    require(user, "manage_workflows")
    validate_workflow_assignees(db, data)
    row = db.get(WorkflowTransition, identity)
    if not row:
        fail("Transição não encontrada.", 404)
    statuses = {item.key for item in db.scalars(select(KanbanColumn))}
    if data.source not in statuses or data.target not in statuses or data.source == data.target:
        fail("Selecione duas etapas diferentes do quadro.")
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc).isoformat()
    audit(
        db,
        user,
        "workflow",
        row.id,
        "transition_updated",
        source=row.source,
        target=row.target,
        enabled=row.enabled,
        work_types=row.work_types or [],
        type_rules=row.type_rules or {},
        conditions=row.conditions or [],
        actions=row.actions or [],
    )
    db.commit()
    return workflow_payload(row)


@app.delete(PREFIX + "/workflows/transitions/{identity}")
def delete_workflow_transition(identity: int, user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_workflows")
    row = db.get(WorkflowTransition, identity)
    if not row:
        fail("Transição não encontrada.", 404)
    audit(db, user, "workflow", row.id, "transition_removed", source=row.source, target=row.target)
    db.delete(row)
    db.commit()
    return {"ok": True}


def automation_payload(row):
    actions = row.actions or [{"action": row.action, "config": row.config or {}}]
    return {
        "id": row.id,
        "name": row.name,
        "trigger": row.trigger,
        "schedule_time": row.schedule_time,
        "schedule_frequency": row.schedule_frequency or "daily",
        "schedule_weekdays": row.schedule_weekdays or [],
        "conditions": row.conditions,
        "action": row.action,
        "config": row.config,
        "actions": actions,
        "enabled": row.enabled,
    }


@app.get(PREFIX + "/automations")
def list_automations(user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_automation")
    return [
        automation_payload(row)
        for row in db.scalars(select(AutomationRule).order_by(AutomationRule.id))
    ]


@app.get(PREFIX + "/automations/runs")
def list_automation_runs(
    limit: int = 50,
    offset: int = 0,
    user=Depends(current_user),
    db=Depends(get_db),
):
    """Return a safe, paginated audit view of automation actions."""
    require(user, "manage_automation")
    if not 1 <= limit <= 100 or offset < 0:
        fail("Paginação inválida.", 422)
    rows = db.execute(
        select(Audit, Task)
        .join(Task, (Audit.entity == "task") & (Audit.entity_id == Task.id))
        .where(Audit.action == "automation_applied")
        .order_by(Audit.created_at.desc(), Audit.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [
        {
            "id": audit_row.id,
            "created_at": audit_row.created_at,
            "rule_id": audit_row.details.get("rule_id"),
            "rule_name": audit_row.details.get("rule_name", "Automação"),
            "trigger": audit_row.details.get("trigger", "unknown"),
            "task_id": task.id,
            "task_key": f"OS-{task.id}",
            "task_title": task.title,
            "actor_name": audit_row.details.get("actor_name", "Sistema"),
            "changed_fields": sorted(
                key for key in (audit_row.details.get("changes") or {})
                if isinstance(key, str) and len(key) <= 80
            ),
            "comments_added": len(audit_row.details.get("comment_ids") or []),
            "watchers_added": len(audit_row.details.get("watcher_ids_added") or []),
            "skipped_actions": len(audit_row.details.get("skipped_actions") or []),
        }
        for audit_row, task in rows
    ]


@app.post(PREFIX + "/automations", status_code=201)
def create_automation(data: AutomationRuleInput, user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_automation")
    for configured in data.actions:
        if configured.action in {"assign_internal_user", "add_watcher"}:
            active_internal_user(db, configured.config["user_id"])
    for identity in data.conditions.get("assignee_user_ids", []):
        active_internal_user(db, identity)
    row = AutomationRule(**data.model_dump(), author_id=user.id)
    db.add(row)
    db.flush()
    audit(
        db,
        user,
        "automation",
        row.id,
        "created",
        name=row.name,
        trigger=row.trigger,
        configured_action=row.action,
        schedule_time=row.schedule_time,
        schedule_frequency=row.schedule_frequency,
        schedule_weekdays=row.schedule_weekdays or [],
    )
    db.commit()
    return automation_payload(row)


@app.put(PREFIX + "/automations/{identity}")
def update_automation(
    identity: int, data: AutomationRuleInput, user=Depends(current_user), db=Depends(get_db)
):
    require(user, "manage_automation")
    for configured in data.actions:
        if configured.action in {"assign_internal_user", "add_watcher"}:
            active_internal_user(db, configured.config["user_id"])
    for identity in data.conditions.get("assignee_user_ids", []):
        active_internal_user(db, identity)
    row = db.get(AutomationRule, identity)
    if not row:
        fail("Automação não encontrada.", 404)
    schedule_before = {
        "time": row.schedule_time,
        "frequency": row.schedule_frequency or "daily",
        "weekdays": row.schedule_weekdays or [],
    }
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc).isoformat()
    audit(
        db,
        user,
        "automation",
        row.id,
        "updated",
        name=row.name,
        enabled=row.enabled,
        schedule_before=schedule_before,
        schedule_after={
            "time": row.schedule_time,
            "frequency": row.schedule_frequency,
            "weekdays": row.schedule_weekdays or [],
        },
    )
    db.commit()
    return automation_payload(row)


@app.delete(PREFIX + "/automations/{identity}")
def delete_automation(identity: int, user=Depends(current_user), db=Depends(get_db)):
    require(user, "manage_automation")
    row = db.get(AutomationRule, identity)
    if not row:
        fail("Automação não encontrada.", 404)
    audit(db, user, "automation", row.id, "deleted", name=row.name)
    db.delete(row)
    db.commit()
    return {"ok": True}


def internal_manager(user):
    if user.role not in {"admin", "manager"}:
        fail("Somente administradores e gestores podem configurar o quadro.", 403)


@app.get(PREFIX + "/board/columns")
def board_columns(user=Depends(current_user), db=Depends(get_db)):
    return [
        {
            "key": row.key,
            "title": row.title,
            "is_system": row.is_system,
            "category": row.category,
            "view_order": row.view_order,
            "wip_limit": row.wip_limit,
        }
        for row in db.scalars(select(KanbanColumn).order_by(KanbanColumn.view_order))
    ]


@app.post(PREFIX + "/board/columns", status_code=201)
def add_board_column(data: KanbanColumnCreate, user=Depends(current_user), db=Depends(get_db)):
    internal_manager(user)
    rows = list(db.scalars(select(KanbanColumn).order_by(KanbanColumn.workflow_order)))
    last_custom = max((row.workflow_order for row in rows if not row.is_system), default=300)
    row = KanbanColumn(
        key="custom_" + uuid4().hex[:16],
        title=data.title,
        is_system=False,
        category="in_progress",
        workflow_order=last_custom + 100,
        view_order=max((column.view_order for column in rows), default=-1) + 1,
    )
    db.add(row)
    audit(db, user, "kanban", 1, "column_created", key=row.key, title=row.title)
    db.commit()
    return {
        "key": row.key,
        "title": row.title,
        "is_system": row.is_system,
        "category": row.category,
        "view_order": row.view_order,
        "wip_limit": row.wip_limit,
    }


@app.put(PREFIX + "/board/columns/order")
def order_board_columns(data: KanbanColumnOrder, user=Depends(current_user), db=Depends(get_db)):
    internal_manager(user)
    rows = list(db.scalars(select(KanbanColumn)))
    by_key = {row.key: row for row in rows}
    if len(data.keys) != len(rows) or set(data.keys) != set(by_key):
        fail("A ordem deve incluir todas as colunas atuais exatamente uma vez.")
    for index, key in enumerate(data.keys):
        by_key[key].view_order = -index - 1
    db.flush()
    for index, key in enumerate(data.keys):
        by_key[key].view_order = index
    audit(db, user, "kanban", 1, "columns_reordered", keys=data.keys)
    db.commit()
    return board_columns(user, db)


@app.put(PREFIX + "/board/columns/{key}")
def rename_board_column(
    key: str, data: KanbanColumnRename, user=Depends(current_user), db=Depends(get_db)
):
    internal_manager(user)
    row = db.get(KanbanColumn, key)
    if not row:
        fail("Coluna não encontrada.", 404)
    if data.title is not None and row.is_system and data.title != row.title:
        fail("As colunas estruturais não podem ser renomeadas.")
    if data.category is not None and ((key == "done") != (data.category == "done")):
        fail("A categoria Concluído é reservada à coluna estrutural Concluído.")
    previous = {"title": row.title, "category": row.category, "wip_limit": row.wip_limit}
    if data.title is not None:
        row.title = data.title
    if data.category is not None:
        row.category = data.category
    if "wip_limit" in data.model_fields_set:
        row.wip_limit = data.wip_limit
    audit(
        db,
        user,
        "kanban",
        1,
        "column_updated",
        key=key,
        previous=previous,
        title=row.title,
        category=row.category,
        wip_limit=row.wip_limit,
    )
    db.commit()
    return {
        "key": row.key,
        "title": row.title,
        "is_system": row.is_system,
        "category": row.category,
        "view_order": row.view_order,
        "wip_limit": row.wip_limit,
    }


@app.delete(PREFIX + "/board/columns/{key}")
def delete_board_column(key: str, user=Depends(current_user), db=Depends(get_db)):
    internal_manager(user)
    row = db.get(KanbanColumn, key)
    if not row:
        fail("Coluna não encontrada.", 404)
    if row.is_system:
        fail("As colunas estruturais não podem ser excluídas.")
    if db.scalar(select(Task.id).where(Task.status == key).limit(1)):
        fail("Mova os cards para outra coluna antes de excluí-la.", 409)
    db.delete(row)
    db.flush()
    remaining = list(db.scalars(select(KanbanColumn).order_by(KanbanColumn.view_order)))
    for index, column in enumerate(remaining):
        column.view_order = -index - 1
    db.flush()
    for index, column in enumerate(remaining):
        column.view_order = index
    audit(db, user, "kanban", 1, "column_deleted", key=key, title=row.title)
    db.commit()
    return {"ok": True}


def saved_filter_payload(row):
    return {
        "id": row.id,
        "name": row.name,
        "query": row.query,
        "shared": row.shared,
        "shared_roles": row.shared_roles or [],
        "shared_group_ids": row.shared_group_ids or [],
        "owner_id": row.owner_id,
        "updated_at": row.updated_at,
    }


def validate_saved_filter(db, user, data):
    if data.shared:
        require(user, "manage_planning")
    validate_shared_groups(db, data.shared_group_ids)
    apply_query(
        select(Task),
        data.query,
        actor_user_id=user.id,
        actor_role=user.role,
        allow_configuration_history=user.role == "admin",
    )


def saved_filter_name_conflict(db, user_id, name, identity=None):
    query = select(SavedFilter.id).where(
        SavedFilter.owner_id == user_id,
        func.lower(SavedFilter.name) == name.casefold(),
    )
    if identity is not None:
        query = query.where(SavedFilter.id != identity)
    return db.scalar(query) is not None


@app.get(PREFIX + "/saved-filters")
def list_saved_filters(
    offset: int = Query(default=0, ge=0, le=100000),
    limit: int = Query(default=100, ge=1, le=200),
    user=Depends(current_user),
    db=Depends(get_db),
):
    query = select(SavedFilter).where(SavedFilter.owner_id == user.id)
    if user.role != "supplier":
        query = select(SavedFilter).where(
            (SavedFilter.owner_id == user.id) | SavedFilter.shared.is_(True)
        )
    rows = db.scalars(query.order_by(SavedFilter.updated_at.desc(), SavedFilter.id.desc()))
    visible = [
        row for row in rows
        if row.owner_id == user.id or shared_with_user(row, user, db)
    ]
    return [saved_filter_payload(row) for row in visible[offset : offset + limit]]


@app.post(PREFIX + "/saved-filters", status_code=201)
def create_saved_filter(data: SavedFilterInput, user=Depends(current_user), db=Depends(get_db)):
    validate_saved_filter(db, user, data)
    if saved_filter_name_conflict(db, user.id, data.name):
        fail("Você já tem um filtro salvo com esse nome.", 409, "DUPLICATE_FILTER")
    row = SavedFilter(owner_id=user.id, **data.model_dump())
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        fail("Você já tem um filtro salvo com esse nome.", 409, "DUPLICATE_FILTER")
    audit(
        db,
        user,
        "saved_filter",
        row.id,
        "created",
        name=row.name,
        shared=row.shared,
        shared_roles=row.shared_roles or [],
        shared_group_ids=row.shared_group_ids or [],
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        fail("Você já tem um filtro salvo com esse nome.", 409, "DUPLICATE_FILTER")
    return saved_filter_payload(row)


@app.put(PREFIX + "/saved-filters/{identity}")
def update_saved_filter(
    identity: int,
    data: SavedFilterInput,
    user=Depends(current_user),
    db=Depends(get_db),
):
    row = db.scalar(
        select(SavedFilter).where(SavedFilter.id == identity, SavedFilter.owner_id == user.id)
    )
    if not row:
        fail("Filtro salvo não encontrado.", 404)
    validate_saved_filter(db, user, data)
    if saved_filter_name_conflict(db, user.id, data.name, identity):
        fail("Você já tem um filtro salvo com esse nome.", 409, "DUPLICATE_FILTER")
    before = {"name": row.name, "query_length": len(row.query), "shared": row.shared}
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc).isoformat()
    audit(
        db,
        user,
        "saved_filter",
        row.id,
        "updated",
        name=row.name,
        before=before,
        shared=row.shared,
        shared_roles=row.shared_roles or [],
        shared_group_ids=row.shared_group_ids or [],
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        fail("Você já tem um filtro salvo com esse nome.", 409, "DUPLICATE_FILTER")
    return saved_filter_payload(row)


@app.delete(PREFIX + "/saved-filters/{identity}")
def delete_saved_filter(identity: int, user=Depends(current_user), db=Depends(get_db)):
    row = db.scalar(
        select(SavedFilter).where(SavedFilter.id == identity, SavedFilter.owner_id == user.id)
    )
    if not row:
        fail("Filtro salvo não encontrado.", 404)
    audit(db, user, "saved_filter", row.id, "deleted", name=row.name, shared=row.shared)
    db.delete(row)
    db.commit()
    return {"ok": True}


def view_payload(row):
    return {
        "id": row.id,
        "name": row.name,
        "layout": row.layout,
        "config": row.config,
        "shared": row.shared,
        "shared_roles": row.shared_roles or [],
        "shared_group_ids": row.shared_group_ids or [],
        "position": row.position,
        "owner_id": row.user_id,
    }


@app.get(PREFIX + "/board/views")
def saved_views(user=Depends(current_user), db=Depends(get_db)):
    query = select(KanbanSavedView).where(KanbanSavedView.user_id == user.id)
    if user.role != "supplier":
        query = select(KanbanSavedView).where(
            (KanbanSavedView.user_id == user.id) | KanbanSavedView.shared.is_(True)
        )
    rows = db.scalars(query.order_by(KanbanSavedView.position, KanbanSavedView.id))
    return [
        view_payload(row)
        for row in rows
        if row.user_id == user.id
        or shared_with_user(row, user, db)
    ]


@app.post(PREFIX + "/board/views", status_code=201)
def create_saved_view(data: SavedViewInput, user=Depends(current_user), db=Depends(get_db)):
    if data.shared:
        require(user, "manage_planning")
    validate_shared_groups(db, data.shared_group_ids)
    row = KanbanSavedView(user_id=user.id, **data.model_dump())
    db.add(row)
    db.commit()
    return view_payload(row)


@app.put(PREFIX + "/board/views/order")
def order_saved_views(data: SavedViewOrder, user=Depends(current_user), db=Depends(get_db)):
    rows = list(db.scalars(select(KanbanSavedView).where(KanbanSavedView.user_id == user.id)))
    by_id = {row.id: row for row in rows}
    if len(data.ids) != len(rows) or set(data.ids) != set(by_id):
        fail("A ordem deve incluir todas as suas visualizações exatamente uma vez.")
    for index, identity in enumerate(data.ids):
        by_id[identity].position = index
    db.commit()
    return saved_views(user, db)


@app.put(PREFIX + "/board/views/{identity}")
def update_saved_view(
    identity: int, data: SavedViewInput, user=Depends(current_user), db=Depends(get_db)
):
    row = db.scalar(
        select(KanbanSavedView).where(
            KanbanSavedView.id == identity, KanbanSavedView.user_id == user.id
        )
    )
    if not row:
        fail("Visualização não encontrada.", 404)
    if data.shared:
        require(user, "manage_planning")
    validate_shared_groups(db, data.shared_group_ids)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return view_payload(row)


@app.delete(PREFIX + "/board/views/{identity}")
def delete_saved_view(identity: int, user=Depends(current_user), db=Depends(get_db)):
    row = db.scalar(
        select(KanbanSavedView).where(
            KanbanSavedView.id == identity, KanbanSavedView.user_id == user.id
        )
    )
    if not row:
        fail("Visualização não encontrada.", 404)
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.put(PREFIX + "/tasks/{identity}/schedule")
def update_task_schedule(
    identity: int, data: TaskScheduleInput, user=Depends(current_user), db=Depends(get_db)
):
    require(user, "create_tasks")
    row = get_task(db, user, identity, True)
    version(row, data.version)
    if row.status == "done":
        fail("Reabra a atividade antes de alterar o cronograma.", 409)
    previous_due = row.due
    if data.planned_start and data.due and data.due < data.planned_start:
        fail("O prazo deve ser igual ou posterior ao início planejado.")
    row.planned_start = data.planned_start.isoformat() if data.planned_start else None
    row.due = data.due.isoformat() if data.due else None
    row.version += 1
    audit(
        db, user, "task", row.id, "schedule_changed", planned_start=row.planned_start, due=row.due
    )
    if previous_due != row.due:
        run_automations(
            db,
            user,
            row,
            "due_changed",
            event_context={"old_due": previous_due, "new_due": row.due},
        )
    db.commit()
    return task_payload(db, user, row)


@app.post(PREFIX + "/tasks", status_code=201)
def create_task(data: TaskCreate, user=Depends(current_user), db=Depends(get_db)):
    require(user, "create_tasks")
    validate_parent(db, None, data.parent_id, data.work_type)
    row = Task(
        title=data.title,
        description=data.description,
        work_type=data.work_type,
        parent_id=data.parent_id,
        labels=[label.model_dump() for label in data.labels or []],
        due=data.due.isoformat() if data.due else None,
        priority=data.priority,
        creator_id=user.id,
    )
    db.add(row)
    db.flush()
    set_supplier(db, user, row, data.supplier_id)
    set_internal_assignee(db, user, row, data.assignee_user_id)
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
    audit(
        db,
        user,
        "task",
        row.id,
        "created",
        estimate_policy=data.estimate_policy,
        status="backlog",
        initial={
            key: getattr(row, key)
            for key in [
                "title",
                "description",
                "work_type",
                "parent_id",
                "labels",
                "due",
                "priority",
                "supplier_id",
                "assignee_user_id",
            ]
        },
    )
    run_automations(db, user, row, "card_created")
    db.commit()
    return task_payload(db, user, row)


@app.put(PREFIX + "/tasks/{identity}")
def update_task(identity: int, data: TaskEdit, user=Depends(current_user), db=Depends(get_db)):
    require(user, "create_tasks")
    row = get_task(db, user, identity, True)
    version(row, data.version)
    validate_parent(db, row, data.parent_id, data.work_type)
    if row.status == "done":
        fail("Reabra a atividade antes de editar.", 409)
    before = {
        key: getattr(row, key)
        for key in [
            "title",
            "description",
            "work_type",
            "parent_id",
            "labels",
            "priority",
            "due",
            "supplier_id",
            "assignee_user_id",
        ]
    }
    set_supplier(db, user, row, data.supplier_id)
    set_internal_assignee(db, user, row, data.assignee_user_id)
    row.title, row.description, row.priority, row.work_type, row.parent_id = (
        data.title,
        data.description,
        data.priority,
        data.work_type,
        data.parent_id,
    )
    if data.labels is not None:
        row.labels = [label.model_dump() for label in data.labels]
    row.due = data.due.isoformat() if data.due else None
    after = {key: getattr(row, key) for key in before}
    audit(
        db,
        user,
        "task",
        row.id,
        "edited",
        changes=changes(before, after),
        task_version=row.version + 1,
    )
    row.version += 1
    if before != after:
        run_automations(db, user, row, "task_updated")
        run_automations(
            db,
            user,
            row,
            "field_changed",
            event_context={
                "changed_fields": [key for key in before if before[key] != after[key]]
            },
        )
        if before["due"] != after["due"]:
            run_automations(
                db,
                user,
                row,
                "due_changed",
                event_context={"old_due": before["due"], "new_due": after["due"]},
            )
        if before["priority"] != after["priority"]:
            run_automations(
                db,
                user,
                row,
                "priority_changed",
                event_context={
                    "old_priority": before["priority"],
                    "new_priority": after["priority"],
                },
            )
        if (
            before["assignee_user_id"] != after["assignee_user_id"]
            or before["supplier_id"] != after["supplier_id"]
        ):
            run_automations(db, user, row, "assignee_changed")
    db.commit()
    return task_payload(db, user, row)


@app.post(PREFIX + "/tasks/{identity}/move")
def move(identity: int, data: Move, user=Depends(current_user), db=Depends(get_db)):
    row = get_task(db, user, identity, True)
    old_status = row.status
    move_task(db, user, row, data)
    if row.status != old_status:
        run_automations(db, user, row, "status_changed")
    db.commit()
    return task_payload(db, user, row)


@app.get(PREFIX + "/tasks/{identity}/hours")
def task_hours_history(
    identity: int,
    offset: int = Query(default=0, ge=0, le=100000),
    limit: int = Query(default=50, ge=1, le=200),
    user=Depends(current_user),
    db=Depends(get_db),
):
    get_task(db, user, identity)
    filters = [Hours.task_id == identity]
    if user.role == "supplier":
        filters.append(Hours.author_id == user.id)
    total = db.scalar(select(func.count(Hours.id)).where(*filters)) or 0
    query = select(Hours, User.username).join(User, User.id == Hours.author_id).where(*filters)
    entries = [
        {
            "version": row.version,
            "estimated_minutes": row.estimated_minutes,
            "used_minutes": row.used_minutes,
            "comment": row.comment or "",
            "author": username,
            "created_at": row.created_at,
        }
        for row, username in db.execute(
            query.order_by(Hours.version.desc()).offset(offset).limit(limit)
        ).all()
    ]
    return {"items": entries, "total": total, "offset": offset, "limit": limit}


@app.put(PREFIX + "/tasks/{identity}/hours")
def put_hours(identity: int, data: HoursInput, user=Depends(current_user), db=Depends(get_db)):
    row = get_task(db, user, identity, True)
    version(row, data.version)
    supplier = supplier_for(db, user)
    if user.role != "supplier" or not supplier or supplier.id != row.supplier_id:
        fail("Somente fornecedor atribuído informa horas.", 403)
    if row.status == "done" or row.approval == "approved":
        fail("Horas aprovadas exigem reabertura formal.", 409)
    if row.status not in {"todo", "production", "review"}:
        fail("Horas previstas podem ser preenchidas em A fazer; horas utilizadas, durante produção ou revisão.")
    if (
        row.status in {"todo", "production"}
        and estimate_required(db, row, "production")
        and data.estimated_minutes <= 0
        or row.status == "review"
        and data.used_minutes <= 0
    ):
        fail("Horas positivas são obrigatórias nesta etapa.")
    if row.status in {"backlog", "todo"} and data.used_minutes:
        fail("Horas utilizadas são informadas durante produção ou revisão.")
    before = {"estimated_minutes": row.estimated_minutes, "used_minutes": row.used_minutes}
    previous_hours_version = row.hours_version
    previous_approval = row.approval
    row.estimated_minutes, row.used_minutes = data.estimated_minutes, data.used_minutes
    row.hours_version += 1
    row.approval = "resubmitted" if row.approval == "rejected" else "pending"
    db.add(
        Hours(
            task_id=row.id,
            version=row.hours_version,
            estimated_minutes=row.estimated_minutes,
            used_minutes=row.used_minutes,
            comment=data.comment.strip() or None,
            author_id=user.id,
        )
    )
    audit(
        db,
        user,
        "task",
        row.id,
        "hours_submitted",
        hours_version=row.hours_version,
        previous_hours_version=previous_hours_version,
        operation="filled" if not previous_hours_version else "edited",
        estimated_minutes=row.estimated_minutes,
        used_minutes=row.used_minutes,
        previous_approval=previous_approval,
        approval=row.approval,
        changes=changes(
            before, {"estimated_minutes": row.estimated_minutes, "used_minutes": row.used_minutes}
        ),
    )
    run_automations(db, user, row, "hours_submitted")
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
    run_automations(db, user, row, "hours_decided")
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
    audit(
        db,
        user,
        "task",
        identity,
        "schema_versioned",
        schema_version=(previous.version + 1 if previous else 1),
        changes=field_changes(previous, fields, values),
    )
    changed_fields = [
        identity
        for identity, value in data.values.items()
        if (previous.values if previous else {}).get(identity) != value
    ]
    if changed_fields:
        run_automations(
            db,
            user,
            row,
            "field_changed",
            event_context={"changed_fields": changed_fields},
        )
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
    audit(
        db,
        user,
        "task",
        identity,
        "values_versioned",
        schema_version=previous.version + 1,
        changes=field_changes(previous, previous.fields, values),
    )
    changed_fields = [
        identity
        for identity, value in data.values.items()
        if previous.values.get(identity) != value
    ]
    if changed_fields:
        run_automations(
            db,
            user,
            row,
            "field_changed",
            event_context={"changed_fields": changed_fields},
        )
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
    audit(
        db,
        user,
        "task",
        task.id,
        "included_in_sprint",
        sprint_id=identity,
        origin="backlog",
        destination="todo",
        estimated_minutes=task.estimated_minutes,
    )
    run_automations(
        db, user, task, "sprint_scope_changed",
        event_context={"action": "added", "sprint_id": identity},
    )
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
    event_time = datetime.now(timezone.utc).isoformat()
    action_details = {}
    if data.action == "start" and sprint.state == "planned":
        sprint.state = "active"
        committed_task_ids = list(
            db.scalars(
                select(SprintTask.task_id).where(
                    SprintTask.sprint_id == identity, SprintTask.active_key == "active"
                )
            )
        )
        action_details["committed_task_ids"] = committed_task_ids
        committed_tasks = [db.get(Task, task_id) for task_id in committed_task_ids]
        action_details["committed_estimates"] = {
            str(task.id): task.estimated_minutes for task in committed_tasks if task
        }
        for task_id in committed_task_ids:
            task = db.get(Task, task_id)
            if task:
                run_automations(db, user, task, "sprint_started")
    elif data.action == "close" and sprint.state == "active":
        sprint.state = "closed"
        for link in db.scalars(
            select(SprintTask).where(
                SprintTask.sprint_id == identity, SprintTask.active_key == "active"
            )
        ):
            task = db.get(Task, link.task_id)
            if task:
                run_automations(db, user, task, "sprint_completed")
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
                "closed_at": event_time,
                "priority": task.priority,
                "title": task.title,
                "description": task.description,
                "labels": task.labels or [],
                "due": task.due,
                "completed_at": completed_at,
                "schema_version_id": schema.id if schema else None,
                "rate_cents": assignment(db, task).rate_cents if assignment(db, task) else None,
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
                    timestamp=event_time,
                )
                run_automations(
                    db, user, task, "sprint_scope_changed",
                    event_context={"action": "removed", "sprint_id": identity},
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
    audit(
        db,
        user,
        "sprint",
        identity,
        data.action,
        reason=data.reason,
        timestamp=event_time,
        **action_details,
    )
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
    users = {actor.id: actor.username for actor in db.scalars(select(User))}
    schema = current_schema(db, db.get(Task, identity)) if entity == "task" else None
    fields = {field["id"]: field for field in schema.fields} if schema else {}
    return [
        {
            "id": row.id,
            "actor_id": row.actor_id,
            "actor_name": row.details.get("actor_name")
            or users.get(row.actor_id, f"Usuário #{row.actor_id}"),
            "action": row.action,
            "created_at": row.created_at,
            "details": visible_details(row.details, user, financial, fields),
        }
        for row in entries
    ]


def dashboard_widget_payload(row):
    return {
        "id": row.id,
        "name": row.name,
        "group_by": row.group_by,
        "group_by_secondary": row.group_by_secondary,
        "jql": row.jql or "",
        "measure": row.measure,
        "chart": row.chart,
        "result_columns": row.result_columns or [],
        "max_results": row.max_results,
        "shared": row.shared,
        "shared_roles": row.shared_roles or [],
        "shared_group_ids": row.shared_group_ids or [],
        "position": row.position,
        "owner_id": row.user_id,
        "dashboard_id": row.dashboard_id,
    }


def visible_widget_query(user, dashboard_id=None):
    query = select(DashboardWidget).where(DashboardWidget.user_id == user.id)
    if user.role != "supplier":
        query = select(DashboardWidget).where(
            (DashboardWidget.user_id == user.id) | DashboardWidget.shared.is_(True)
        )
    if dashboard_id is not None:
        query = query.where(DashboardWidget.dashboard_id == dashboard_id)
    return query


def widget_visible_to(row, user, db):
    return row.user_id == user.id or shared_with_user(row, user, db)


def default_dashboard(db, user):
    row = db.scalar(
        select(Dashboard).where(
            Dashboard.user_id == user.id, Dashboard.is_default.is_(True)
        )
    )
    if row is None:
        row = Dashboard(user_id=user.id, name="Visão geral", is_default=True)
        db.add(row)
        db.flush()
    return row


def accessible_dashboard(db, user, identity):
    row = db.get(Dashboard, identity)
    if row is None:
        return None
    if row.user_id == user.id:
        return row
    if user.role == "supplier":
        return None
    widgets = db.scalars(
        select(DashboardWidget).where(
            DashboardWidget.dashboard_id == row.id,
            DashboardWidget.shared.is_(True),
        )
    )
    return row if any(
        widget_visible_to(widget, user, db)
        and (widget.measure != "cost_cents" or allowed(user, "view_financial"))
        for widget in widgets
    ) else None


def dashboard_payload(row, *, owner_name=None, read_only=False):
    return {
        "id": row.id,
        "name": row.name,
        "owner_id": row.user_id,
        "owner_name": owner_name,
        "is_default": row.is_default,
        "read_only": read_only,
    }


@app.get(PREFIX + "/dashboard/dashboards")
def list_dashboards(user=Depends(current_user), db=Depends(get_db)):
    if user.role == "supplier":
        return []
    own = list(
        db.scalars(
            select(Dashboard)
            .where(Dashboard.user_id == user.id)
            .order_by(Dashboard.is_default.desc(), Dashboard.name, Dashboard.id)
        )
    )
    if not any(row.is_default for row in own):
        own.insert(0, default_dashboard(db, user))
        db.commit()
    payloads = [dashboard_payload(row) for row in own]
    shared = db.scalars(
        select(Dashboard)
        .join(DashboardWidget, DashboardWidget.dashboard_id == Dashboard.id)
        .where(Dashboard.user_id != user.id, DashboardWidget.shared.is_(True))
        .distinct()
        .order_by(Dashboard.name, Dashboard.id)
    )
    for row in shared:
        if accessible_dashboard(db, user, row.id):
            owner = db.get(User, row.user_id)
            payloads.append(
                dashboard_payload(row, owner_name=owner.username if owner else None, read_only=True)
            )
    return payloads


@app.post(PREFIX + "/dashboard/dashboards", status_code=201)
def create_dashboard(data: DashboardInput, user=Depends(current_user), db=Depends(get_db)):
    if user.role == "supplier":
        fail("Fornecedores não podem criar dashboards.", 403, "FORBIDDEN")
    default_dashboard(db, user)
    row = Dashboard(user_id=user.id, name=data.name, is_default=False)
    db.add(row)
    try:
        db.flush()
        audit(db, user, "dashboard", row.id, "created", name=row.name)
        db.commit()
    except IntegrityError:
        db.rollback()
        fail("Já existe um dashboard com esse nome.", 409, "DASHBOARD_NAME_CONFLICT")
    return dashboard_payload(row)


@app.put(PREFIX + "/dashboard/dashboards/{identity}")
def rename_dashboard(identity: int, data: DashboardInput, user=Depends(current_user), db=Depends(get_db)):
    row = db.scalar(
        select(Dashboard).where(Dashboard.id == identity, Dashboard.user_id == user.id)
    )
    if row is None:
        fail("Dashboard não encontrado.", 404)
    previous = row.name
    row.name = data.name
    try:
        audit(db, user, "dashboard", row.id, "renamed", previous=previous, name=row.name)
        db.commit()
    except IntegrityError:
        db.rollback()
        fail("Já existe um dashboard com esse nome.", 409, "DASHBOARD_NAME_CONFLICT")
    return dashboard_payload(row)


@app.delete(PREFIX + "/dashboard/dashboards/{identity}")
def delete_dashboard(identity: int, user=Depends(current_user), db=Depends(get_db)):
    row = db.scalar(
        select(Dashboard).where(Dashboard.id == identity, Dashboard.user_id == user.id)
    )
    if row is None:
        fail("Dashboard não encontrado.", 404)
    if row.is_default:
        fail("O dashboard padrão não pode ser removido.", 409, "DEFAULT_DASHBOARD")
    if db.scalar(
        select(DashboardWidget.id).where(DashboardWidget.dashboard_id == row.id).limit(1)
    ) is not None:
        fail("Remova os widgets antes de excluir este dashboard.", 409, "DASHBOARD_NOT_EMPTY")
    audit(db, user, "dashboard", row.id, "deleted", name=row.name)
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.get(PREFIX + "/dashboard/widgets")
def list_dashboard_widgets(
    dashboard_id: int | None = None, user=Depends(current_user), db=Depends(get_db)
):
    if user.role == "supplier":
        return []
    had_default = db.scalar(
        select(Dashboard.id).where(
            Dashboard.user_id == user.id, Dashboard.is_default.is_(True)
        )
    )
    selected = default_dashboard(db, user) if dashboard_id is None else accessible_dashboard(db, user, dashboard_id)
    if selected is None:
        fail("Dashboard não encontrado.", 404)
    if dashboard_id is None and had_default is None:
        db.commit()
    rows = [
        row
        for row in db.scalars(
            visible_widget_query(user, selected.id).order_by(DashboardWidget.position, DashboardWidget.id)
        )
        if widget_visible_to(row, user, db)
        and (row.measure != "cost_cents" or allowed(user, "view_financial"))
    ]
    positions = {
        row.widget_id: row.position
        for row in db.scalars(
            select(DashboardWidgetPosition).where(DashboardWidgetPosition.user_id == user.id)
        )
    }
    payloads = []
    for row in rows:
        payload = dashboard_widget_payload(row)
        payload["position"] = positions.get(row.id, row.position)
        payloads.append(payload)
    return sorted(payloads, key=lambda item: (item["position"], item["id"]))


@app.post(PREFIX + "/dashboard/widgets", status_code=201)
def create_dashboard_widget(
    data: DashboardWidgetInput, user=Depends(current_user), db=Depends(get_db)
):
    if user.role == "supplier":
        fail("Relatórios personalizados estão disponíveis apenas a usuários internos.", 403, "FORBIDDEN")
    if data.shared:
        require(user, "manage_planning")
    from .dashboard_widgets import filtered_widget_query

    filtered_widget_query(select(Task), data.jql, user.role, user.id)
    validate_shared_groups(db, data.shared_group_ids)
    if data.measure == "cost_cents":
        require(user, "view_financial")
    payload = data.model_dump()
    requested_dashboard = payload.pop("dashboard_id")
    selected = (
        default_dashboard(db, user)
        if requested_dashboard is None
        else accessible_dashboard(db, user, requested_dashboard)
    )
    if selected is None or selected.user_id != user.id:
        fail("Só é possível adicionar widgets a um dashboard próprio.", 403, "FORBIDDEN")
    row = DashboardWidget(user_id=user.id, dashboard_id=selected.id, **payload)
    db.add(row)
    db.flush()
    audit(db, user, "dashboard_widget", row.id, "created", name=row.name, shared=row.shared)
    db.commit()
    return dashboard_widget_payload(row)


@app.put(PREFIX + "/dashboard/widgets/order")
def reorder_dashboard_widgets(
    data: DashboardWidgetOrderInput, user=Depends(current_user), db=Depends(get_db)
):
    if user.role == "supplier":
        fail("Relatórios personalizados estão disponíveis apenas a usuários internos.", 403, "FORBIDDEN")
    selected = (
        default_dashboard(db, user)
        if data.dashboard_id is None
        else accessible_dashboard(db, user, data.dashboard_id)
    )
    if selected is None:
        fail("Dashboard não encontrado.", 404)
    visible = [
        row
        for row in db.scalars(visible_widget_query(user, selected.id))
        if widget_visible_to(row, user, db)
        and (row.measure != "cost_cents" or allowed(user, "view_financial"))
    ]
    visible_ids = {row.id for row in visible}
    if set(data.ids) != visible_ids:
        fail("Os widgets visíveis mudaram. Atualize o painel antes de reorganizar.", 409)

    saved = {
        row.widget_id: row
        for row in db.scalars(
            select(DashboardWidgetPosition).where(DashboardWidgetPosition.user_id == user.id)
        )
    }
    for position, widget_id in enumerate(data.ids):
        row = saved.get(widget_id)
        if row is None:
            db.add(
                DashboardWidgetPosition(
                    user_id=user.id, widget_id=widget_id, position=position
                )
            )
        else:
            row.position = position
    audit(db, user, "dashboard_widget_layout", user.id, "reordered", count=len(data.ids))
    db.commit()
    return list_dashboard_widgets(selected.id, user, db)


@app.put(PREFIX + "/dashboard/widgets/{identity}")
def update_dashboard_widget(
    identity: int, data: DashboardWidgetInput, user=Depends(current_user), db=Depends(get_db)
):
    if user.role == "supplier":
        fail("Relatórios personalizados estão disponíveis apenas a usuários internos.", 403, "FORBIDDEN")
    row = db.scalar(
        select(DashboardWidget).where(
            DashboardWidget.id == identity, DashboardWidget.user_id == user.id
        )
    )
    if not row:
        fail("Widget não encontrado.", 404)
    requested_dashboard = data.dashboard_id
    if requested_dashboard is not None:
        selected = accessible_dashboard(db, user, requested_dashboard)
        if selected is None or selected.user_id != user.id:
            fail("Só é possível mover widgets para um dashboard próprio.", 403, "FORBIDDEN")
    if data.shared:
        require(user, "manage_planning")
    from .dashboard_widgets import filtered_widget_query

    filtered_widget_query(select(Task), data.jql, user.role, user.id)
    validate_shared_groups(db, data.shared_group_ids)
    if data.measure == "cost_cents":
        require(user, "view_financial")
    for key, value in data.model_dump(exclude={"dashboard_id"}).items():
        setattr(row, key, value)
    if requested_dashboard is not None:
        row.dashboard_id = requested_dashboard
    audit(db, user, "dashboard_widget", row.id, "updated", name=row.name, shared=row.shared)
    db.commit()
    return dashboard_widget_payload(row)


@app.delete(PREFIX + "/dashboard/widgets/{identity}")
def delete_dashboard_widget(identity: int, user=Depends(current_user), db=Depends(get_db)):
    if user.role == "supplier":
        fail("Relatórios personalizados estão disponíveis apenas a usuários internos.", 403, "FORBIDDEN")
    row = db.scalar(
        select(DashboardWidget).where(
            DashboardWidget.id == identity, DashboardWidget.user_id == user.id
        )
    )
    if not row:
        fail("Widget não encontrado.", 404)
    audit(db, user, "dashboard_widget", row.id, "deleted", name=row.name)
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.get(PREFIX + "/dashboard/widgets/{identity}/data")
def dashboard_widget_data(
    identity: int,
    jql: str = Query(default="", max_length=1000),
    q: str = "",
    status: str | None = None,
    sprint_id: int | None = None,
    supplier_id: int | None = None,
    starts: date | None = None,
    ends: date | None = None,
    user=Depends(current_user),
    db=Depends(get_db),
):
    if user.role == "supplier":
        fail("Relatórios personalizados estão disponíveis apenas a usuários internos.", 403, "FORBIDDEN")
    row = db.scalar(visible_widget_query(user).where(DashboardWidget.id == identity))
    if not row or not widget_visible_to(row, user, db):
        fail("Widget não encontrado.", 404)
    if row.measure == "cost_cents":
        require(user, "view_financial")
    from .services import cost_cents
    from .dashboard_widgets import (
        created_resolved_series,
        current_status_age_days,
        current_status_entry_times,
        widget_group_keys,
        widget_group_sort_key,
        widget_measure_value,
    )

    grouped = {}
    group_counts = {}
    task_query = filtered_tasks(db, user, q, status, sprint_id, supplier_id, starts, ends)
    from .dashboard_widgets import filtered_widget_query

    task_query = filtered_widget_query(task_query, row.jql or "", user.role, user.id)
    task_query = filtered_widget_query(task_query, jql, user.role, user.id)
    if row.chart == "filter_results":
        total_results = db.scalar(
            select(func.count()).select_from(task_query.order_by(None).subquery())
        ) or 0
        tasks = list(
            db.scalars(task_query.order_by(Task.priority, Task.id).limit(row.max_results))
        )
        from .dashboard_widgets import WORK_TYPE_LABELS

        column_labels = {
            "key": "Chave",
            "summary": "Resumo",
            "status": "Etapa",
            "priority": "Prioridade",
            "assignee": "Responsável",
            "supplier": "Fornecedor",
            "sprint": "Sprint",
            "due": "Prazo",
            "created_at": "Criado em",
            "work_type": "Tipo",
        }
        rows = []
        for task in tasks:
            status_column = db.get(KanbanColumn, task.status)
            assignee = db.get(User, task.assignee_user_id) if task.assignee_user_id else None
            supplier = db.get(Supplier, task.supplier_id) if task.supplier_id else None
            sprint = db.get(Sprint, task.sprint_id) if task.sprint_id else None
            values = {
                "key": f"OS-{task.id}",
                "summary": task.title,
                "status": status_column.title if status_column else task.status,
                "priority": task.priority,
                "assignee": assignee.username if assignee else "Não atribuído",
                "supplier": supplier.name if supplier else "Não atribuído",
                "sprint": sprint.name if sprint else "Sem sprint",
                "due": task.due or "Sem prazo",
                "created_at": task.created_at,
                "work_type": WORK_TYPE_LABELS.get(task.work_type, task.work_type),
            }
            rows.append(
                {key: values[key] for key in row.result_columns if key in column_labels}
            )
        return {
            "id": row.id,
            "name": row.name,
            "group_by": row.group_by,
            "measure": row.measure,
            "chart": row.chart,
            "result_columns": [key for key in row.result_columns if key in column_labels],
            "max_results": row.max_results,
            "total": total_results,
            "data": rows,
        }
    tasks = list(db.scalars(task_query))
    status_entered_at_by_task = (
        current_status_entry_times(db, tasks)
        if row.measure == "avg_current_status_days"
        else {}
    )
    resolved_at_by_task = {}
    if tasks and (
        row.group_by == "resolved_month"
        or row.measure in {"avg_resolution_days", "created_vs_resolved"}
    ):
        task_ids = [task.id for task in tasks]
        events = db.scalars(
            select(Audit)
            .where(
                Audit.entity == "task",
                Audit.entity_id.in_(task_ids),
                Audit.action == "status_changed",
            )
            .order_by(Audit.created_at.desc(), Audit.id.desc())
        )
        for event in events:
            if event.entity_id not in resolved_at_by_task and (event.details or {}).get("destination") == "done":
                resolved_at_by_task[event.entity_id] = event.created_at
    if row.measure == "created_vs_resolved":
        return {
            "id": row.id,
            "name": row.name,
            "group_by": row.group_by,
            "measure": row.measure,
            "chart": row.chart,
            "data": created_resolved_series(tasks, resolved_at_by_task),
        }
    for task in tasks:
        resolved_at = resolved_at_by_task.get(task.id)
        if row.measure == "cost_cents":
            amount = cost_cents(db, task)
        elif row.measure == "avg_current_status_days":
            amount = current_status_age_days(status_entered_at_by_task.get(task.id))
        else:
            amount = widget_measure_value(task, row.measure, resolved_at=resolved_at)
        if amount is None:
            continue
        primary_keys = widget_group_keys(
            db,
            task,
            row.group_by,
            show_parent_details=user.role != "supplier",
            resolved_at=resolved_at,
        )
        secondary_keys = widget_group_keys(
            db,
            task,
            row.group_by_secondary,
            show_parent_details=user.role != "supplier",
            resolved_at=resolved_at,
        ) if row.group_by_secondary else [None]
        for primary in primary_keys:
            for secondary in secondary_keys:
                key = (primary, secondary) if row.group_by_secondary else primary
                grouped[key] = grouped.get(key, 0) + amount
                if row.measure in {"avg_open_age_days", "avg_resolution_days", "avg_current_status_days"}:
                    group_counts[key] = group_counts.get(key, 0) + 1
    if row.measure in {"avg_open_age_days", "avg_resolution_days", "avg_current_status_days"}:
        grouped = {
            key: round(total / group_counts[key], 1)
            for key, total in grouped.items()
            if group_counts.get(key)
        }
    return {
        "id": row.id,
        "name": row.name,
        "group_by": row.group_by,
        "group_by_secondary": row.group_by_secondary,
        "measure": row.measure,
        "chart": row.chart,
        "data": [
            ({"row": key[0], "column": key[1], "value": value} if row.group_by_secondary else {"name": key, "value": value})
            for key, value in sorted(
                grouped.items(),
                key=(lambda item: (
                    widget_group_sort_key((item[0][0], item[1]), row.group_by),
                    widget_group_sort_key((item[0][1], item[1]), row.group_by_secondary),
                )) if row.group_by_secondary else (
                    lambda item: widget_group_sort_key(item, row.group_by)
                ),
            )
        ],
    }


@app.get(PREFIX + "/dashboard")
def dashboard(
    field_filters: str = Query(default="[]", max_length=12000),
    jql: str = Query(default="", max_length=1000),
    status: str | None = None,
    sprint_id: int | None = None,
    supplier_id: int | None = None,
    starts: date | None = None,
    ends: date | None = None,
    user=Depends(current_user),
    db=Depends(get_db),
):
    from .reporting import records, indicators

    from .report_filters import filter_context

    context = filter_context(db, user, field_filters, sprint_id)
    rows = records(db, user, status, sprint_id, supplier_id, starts, ends, context, jql=jql)
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
        sprint_rows = records(
            db, user, status, sprint.id, supplier_id, starts, ends, context, jql=jql
        )
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


@app.get(PREFIX + "/reports/agile/{sprint_id}")
def agile_sprint_report(
    sprint_id: int,
    jql: str = "",
    cycle_start_status: str = Query(default="production", max_length=60),
    cycle_end_status: str = Query(default="done", max_length=60),
    user=Depends(current_user),
    db=Depends(get_db),
):
    if user.role == "supplier":
        fail("Relatórios disponíveis apenas a usuários internos.", 403)
    status_keys = {row.key for row in db.scalars(select(KanbanColumn))}
    if (
        cycle_start_status not in status_keys
        or cycle_end_status not in status_keys
        or cycle_start_status == cycle_end_status
    ):
        fail("Selecione duas etapas diferentes existentes no quadro.")
    from .agile_reporting import sprint_agile_report

    return sprint_agile_report(
        db,
        sprint_id,
        jql,
        cycle_start_status=cycle_start_status,
        cycle_end_status=cycle_end_status,
        allow_configuration_history=user.role == "admin",
        actor_user_id=user.id,
        actor_role=user.role,
    )


@app.get(PREFIX + "/reports/planning/{kind}/{identity}")
def planning_progress_report(
    kind: str,
    identity: int,
    jql: str = "",
    user=Depends(current_user),
    db=Depends(get_db),
):
    if user.role == "supplier":
        fail("Relatórios disponíveis apenas a usuários internos.", 403)
    from .planning_reporting import planning_report

    return planning_report(
        db,
        kind,
        identity,
        jql,
        allow_configuration_history=user.role == "admin",
        actor_user_id=user.id,
    )


@app.get(PREFIX + "/exports/{format}")
def export(
    format: str,
    financial: bool = False,
    analysis: bool = False,
    idle_days: int = Query(default=7, ge=1, le=3650),
    min_phase_hours: str | None = Query(default=None, max_length=30),
    overdue_only: bool = False,
    only_reopened: bool = False,
    approval_state: str | None = Query(
        default=None, pattern="^(pending|approved|rejected|resubmitted)$"
    ),
    field_filters: str = Query(default="[]", max_length=12000),
    jql: str = Query(default="", max_length=1000),
    status: str | None = None,
    sprint_id: int | None = None,
    supplier_id: int | None = None,
    starts: date | None = None,
    ends: date | None = None,
    user=Depends(current_user),
    db=Depends(get_db),
):
    if user.role == "supplier":
        fail("Relatórios disponíveis apenas para usuários internos.", 403)
    require(user, "export_data")
    if financial:
        require(user, "export_financial")
        require(user, "view_financial")
        if user.role not in {"admin", "manager"}:
            fail("Exportação financeira restrita.", 403)
    if format not in {"xlsx", "pdf", "html"}:
        fail("Formato indisponível.", 404)
    from .reporting import records, indicators
    from .exports import build_export

    from .report_filters import filter_context

    context = filter_context(db, user, field_filters, sprint_id)
    rows = records(
        db, user, status, sprint_id, supplier_id, starts, ends, context, jql=jql
    )
    from .report_filters import filter_summary

    if any(
        item["financial"] and any(rule.field == item["key"] for rule in context[0])
        for item in context[1]
    ):
        require(user, "export_financial")
    filters = {
        "campos": filter_summary(*context),
        "jql": jql,
        "status": status,
        "sprint_id": sprint_id,
        "supplier_id": supplier_id,
        "starts": str(starts or ""),
        "ends": str(ends or ""),
    }
    if analysis or format == "html":
        from .analytics import report as operational_report
        from .analytics_exports import build_export as build_operational_export

        criteria = {
            "field_filters": field_filters,
            "jql": jql,
            "status": status,
            "sprint_id": sprint_id,
            "supplier_id": supplier_id,
            "starts": starts,
            "ends": ends,
            "min_phase_hours": min_phase_hours,
            "overdue_only": overdue_only,
            "only_reopened": only_reopened,
            "approval_state": approval_state,
        }
        result = operational_report(db, user, criteria, idle_days=idle_days)
        filters.update(
            min_phase_hours=min_phase_hours,
            overdue_only=overdue_only,
            only_reopened=only_reopened,
            approval_state=approval_state,
            idle_days=idle_days,
        )
        buffer, media = build_operational_export(format, result, financial, filters)
        rows = result["items"]
    else:
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

from .report_routes import router as report_router

app.include_router(report_router)


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
        previous_priority = row.priority
        row.priority = base + index
        row.version += 1
        audit(
            db,
            user,
            "task",
            row.id,
            "reordered",
            priority=row.priority,
            previous_priority=previous_priority,
        )
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
