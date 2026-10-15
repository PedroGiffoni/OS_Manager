import hashlib
import re
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from pydantic import Field
from .db import get_db
from .models import Attachment, Comment, User
from .schemas import Input
from .security import current_user, allowed
from .services import get_task, fail, audit

router = APIRouter(prefix="/api/v1")


class CommentInput(Input):
    body: str = Field(min_length=1, max_length=5000)


def can_write(user):
    if user.role not in {"supplier", "admin", "manager"} and not allowed(user, "create_tasks"):
        fail("Sem autorização para colaborar nesta atividade.", 403)


@router.get("/directory/users")
def directory(user=Depends(current_user), db=Depends(get_db)):
    query = select(User).where(User.active.is_(True))
    if user.role == "supplier":
        query = query.where(User.id == user.id)
    return [{"id": row.id, "name": row.username} for row in db.scalars(query.limit(200))]


@router.get("/tasks/{identity}/comments")
def comments(identity: int, user=Depends(current_user), db=Depends(get_db)):
    get_task(db, user, identity)
    return [
        {
            "id": row.id,
            "body": row.body,
            "author_id": row.author_id,
            "created_at": row.created_at,
        }
        for row in db.scalars(
            select(Comment).where(Comment.task_id == identity).order_by(Comment.id)
        )
    ]


@router.post("/tasks/{identity}/comments", status_code=201)
def add_comment(identity: int, data: CommentInput, user=Depends(current_user), db=Depends(get_db)):
    task = get_task(db, user, identity, True)
    can_write(user)
    if task.status == "done":
        fail("Reabra a atividade antes de adicionar comentário.", 409)
    row = Comment(task_id=identity, body=data.body, author_id=user.id)
    db.add(row)
    audit(db, user, "task", identity, "comment_added")
    db.commit()
    return {"id": row.id}


@router.get("/tasks/{identity}/attachments")
def attachments(identity: int, user=Depends(current_user), db=Depends(get_db)):
    get_task(db, user, identity)
    return [
        {
            "id": row.id,
            "name": row.name,
            "size": row.size,
            "sha256": row.sha256,
            "author_id": row.author_id,
            "created_at": row.created_at,
        }
        for row in db.scalars(
            select(Attachment).where(Attachment.task_id == identity).order_by(Attachment.id)
        )
    ]


@router.post("/tasks/{identity}/attachments", status_code=201)
async def add_attachment(
    identity: int,
    file: UploadFile = File(...),
    user=Depends(current_user),
    db=Depends(get_db),
):
    task = get_task(db, user, identity, True)
    can_write(user)
    if task.status == "done":
        fail("Reabra a atividade antes de anexar.", 409)
    content = await file.read(5 * 1024 * 1024 + 1)
    if not content or len(content) > 5 * 1024 * 1024:
        fail("Anexo deve conter de 1 byte a 5 MiB.")
    kind = file.content_type
    valid = (
        (kind == "application/pdf" and content.startswith(b"%PDF-"))
        or (kind == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n"))
        or (kind == "image/jpeg" and content.startswith(b"\xff\xd8\xff"))
    )
    if kind == "text/plain":
        try:
            content.decode("utf-8")
            valid = b"\x00" not in content
        except UnicodeDecodeError:
            pass
    if not valid:
        fail("Envie PDF, PNG, JPEG ou texto UTF-8 válido.")
    name = re.sub(r"[^\w .()-]", "_", (file.filename or "anexo").replace("\\", "/").split("/")[-1])[
        :120
    ]
    row = Attachment(
        task_id=identity,
        name=name,
        media_type=kind,
        content=content,
        size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        author_id=user.id,
    )
    db.add(row)
    audit(db, user, "task", identity, "attachment_added")
    db.commit()
    return {"id": row.id}


@router.get("/attachments/{identity}")
def download_attachment(identity: int, user=Depends(current_user), db=Depends(get_db)):
    row = db.get(Attachment, identity)
    if not row:
        fail("Anexo não encontrado.", 404)
    get_task(db, user, row.task_id)
    return Response(
        row.content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename=\"attachment-{identity}\"; filename*=UTF-8''"
            + __import__("urllib.parse", fromlist=["quote"]).quote(row.name),
            "X-Content-Type-Options": "nosniff",
        },
    )
