from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    ForeignKey,
    ForeignKeyConstraint,
    JSON,
    Text,
    LargeBinary,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


def now():
    return datetime.now(timezone.utc).isoformat()


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[str] = mapped_column(String, primary_key=True)


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[str] = mapped_column(String, primary_key=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(ForeignKey("roles.id"))
    grants: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    csrf: Mapped[str] = mapped_column(String)
    expires: Mapped[str] = mapped_column(String)


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    function: Mapped[str] = mapped_column(String(160))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), unique=True)


class Rate(Base):
    __tablename__ = "supplier_hourly_rates"
    __table_args__ = (CheckConstraint("cents > 0"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    cents: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(String, default=now)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text, default="")


class Sprint(Base):
    __tablename__ = "sprints"
    archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", index=True)
    __table_args__ = (CheckConstraint("ends >= starts"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    objective: Mapped[str] = mapped_column(Text)
    starts: Mapped[str] = mapped_column(String)
    ends: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String, default="planned")
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version}


class Task(Base):
    __tablename__ = "tasks"
    archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", index=True)
    __table_args__ = (CheckConstraint("estimated_minutes >= 0 AND used_minutes >= 0"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="backlog", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    due: Mapped[str | None] = mapped_column(String, nullable=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), index=True)
    sprint_id: Mapped[int | None] = mapped_column(ForeignKey("sprints.id"), index=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=0)
    used_minutes: Mapped[int] = mapped_column(Integer, default=0)
    hours_version: Mapped[int] = mapped_column(Integer, default=0)
    approval: Mapped[str] = mapped_column(String, default="pending")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String, default=now)
    __mapper_args__ = {"version_id_col": version}


class Assignment(Base):
    __tablename__ = "task_assignments"
    __table_args__ = (UniqueConstraint("task_id", "active_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    rate_id: Mapped[int] = mapped_column(ForeignKey("supplier_hourly_rates.id"))
    rate_cents: Mapped[int] = mapped_column(Integer)
    active_key: Mapped[str | None] = mapped_column(String, default="active", nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=now)


class SprintTask(Base):
    __tablename__ = "sprint_tasks"
    __table_args__ = (UniqueConstraint("task_id", "active_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    sprint_id: Mapped[int] = mapped_column(ForeignKey("sprints.id"))
    active_key: Mapped[str | None] = mapped_column(String, default="active", nullable=True)
    final_status: Mapped[str | None] = mapped_column(String, nullable=True)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")


class SchemaVersion(Base):
    __tablename__ = "task_schema_versions"
    __table_args__ = (UniqueConstraint("task_id", "version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    fields: Mapped[list] = mapped_column(JSON)
    values: Mapped[dict] = mapped_column(JSON)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(String, default=now)


class Hours(Base):
    __tablename__ = "task_hours"
    __table_args__ = (UniqueConstraint("task_id", "version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    estimated_minutes: Mapped[int] = mapped_column(Integer)
    used_minutes: Mapped[int] = mapped_column(Integer)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(String, default=now)


class Approval(Base):
    __tablename__ = "hour_approvals"
    __table_args__ = (
        UniqueConstraint("task_id", "hours_version"),
        ForeignKeyConstraint(
            ["task_id", "hours_version"],
            ["task_hours.task_id", "task_hours.version"],
            name="fk_approval_hours_version",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    hours_version: Mapped[int] = mapped_column(Integer)
    sprint_id: Mapped[int | None] = mapped_column(
        ForeignKey("sprints.id"), nullable=True, index=True
    )
    assignment_id: Mapped[int] = mapped_column(ForeignKey("task_assignments.id"))
    approved: Mapped[bool] = mapped_column(Boolean)
    used_minutes: Mapped[int] = mapped_column(Integer)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Audit(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    entity: Mapped[str] = mapped_column(String, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    action: Mapped[str] = mapped_column(String)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Attachment(Base):
    __tablename__ = "attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    media_type: Mapped[str] = mapped_column(String(100))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(String, default=now)


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(String, default=now)
