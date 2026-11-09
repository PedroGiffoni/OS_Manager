import hashlib
import secrets
from datetime import datetime, timezone
from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from .db import get_db
from .models import User, Session, Supplier, Board, BoardMember

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
    "manage_planning",
    "manage_capacity",
    "manage_workflows",
    "manage_automation",
    "manage_integrations",
}
INTERNAL_WORKSPACE_PERMISSIONS = {
    "manage_planning",
    "manage_capacity",
    "manage_workflows",
    "manage_automation",
}


def effective_permissions(user):
    """Workspace planning features are open to internal accounts, never suppliers."""
    if user.role == "supplier":
        return set()
    if user.role == "admin":
        return set(PERMISSIONS)
    return set(user.grants) | INTERNAL_WORKSPACE_PERMISSIONS


def allowed(user, permission):
    return permission in effective_permissions(user)


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
    requested_board = request.headers.get("X-Board-ID")
    available = list_visible_boards(db, user)
    if requested_board:
        try:
            identity = int(requested_board)
        except ValueError:
            raise HTTPException(403, {"code": "BOARD_ACCESS_DENIED", "message": "Quadro indisponível."})
        board = next((row for row in available if row.id == identity), None)
    else:
        board = available[0] if available else None
    if not board:
        raise HTTPException(403, {"code": "BOARD_ACCESS_DENIED", "message": "Você não tem acesso a um quadro ativo."})
    db.info["board_id"] = board.id
    db.info["user_role"] = user.role
    user.active_board_id = board.id
    request.state.board_id = board.id
    return user


def list_visible_boards(db, user):
    query = select(Board).where(Board.active.is_(True)).order_by(Board.name, Board.id)
    if user.role != "admin":
        query = query.join(BoardMember, BoardMember.board_id == Board.id).where(BoardMember.user_id == user.id)
    return list(db.scalars(query))


def board_list_payload(db, user):
    visible = list_visible_boards(db, user)
    if user.role == "admin":
        members = {}
        for row in visible:
            members[row.id] = [
                {"id": member.id, "username": member.username, "role": member.role, "active": member.active}
                for member in db.scalars(
                    select(User)
                    .join(BoardMember, BoardMember.user_id == User.id)
                    .where(BoardMember.board_id == row.id)
                    .order_by(User.username)
                )
            ]
    return [
        {"id": row.id, "name": row.name, "description": row.description,
         "active": row.active, "members": members.get(row.id, []) if user.role == "admin" else [],
         "is_default": row.id == 1}
        for row in visible
    ]


def supplier_for(db, user):
    return db.scalar(select(Supplier).where(Supplier.user_id == user.id))


def active_internal_user(db, identity):
    """Resolve an assignable internal account without exposing supplier accounts."""
    if identity is None:
        return None
    user = db.get(User, identity)
    if not user or not user.active or user.role == "supplier":
        raise HTTPException(
            422,
            {"code": "INVALID_ASSIGNEE", "message": "Responsável interno indisponível."},
        )
    return user
