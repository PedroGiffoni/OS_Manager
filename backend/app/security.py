import hashlib
import secrets
from datetime import datetime, timezone
from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from .db import get_db
from .models import User, Session, Supplier

hasher = PasswordHasher()
PERMISSIONS = {
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
    "manage_users",
}


def allowed(user, permission):
    return user.role != "supplier" and (user.role == "admin" or permission in user.grants)


def require(user, permission):
    if not allowed(user, permission):
        raise HTTPException(403, {"code": "FORBIDDEN", "message": "Permissão insuficiente."})


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def current_user(request: Request, db=Depends(get_db)):
    session = db.get(Session, digest(request.cookies.get("session", "")))
    if not session or session.expires <= datetime.now(timezone.utc).isoformat():
        raise HTTPException(401, {"code": "UNAUTHENTICATED", "message": "Entre para continuar."})
    user = db.get(User, session.user_id)
    if not user or not user.active:
        raise HTTPException(401, "Sessão inválida.")
    request.state.actor_id = user.id
    request.state.db_bind = db.get_bind()
    if request.method not in {"GET", "HEAD", "OPTIONS"} and not secrets.compare_digest(
        request.headers.get("X-CSRF-Token", ""), session.csrf
    ):
        raise HTTPException(403, {"code": "CSRF", "message": "Recarregue a sessão."})
    request.state.session = session
    return user


def supplier_for(db, user):
    return db.scalar(select(Supplier).where(Supplier.user_id == user.id))
