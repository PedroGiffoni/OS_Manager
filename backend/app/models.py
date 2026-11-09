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
    Index,
    false,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
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
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    profile_photo: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    profile_photo_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    profile_photo_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


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
    archived: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), index=True
    )
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
    archived: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), index=True
    )
    __table_args__ = (
        CheckConstraint(
            "estimated_minutes >= 0 AND used_minutes >= 0",
            name="ck_task_hours_nonnegative",
        ),
        CheckConstraint(
            "resolution IS NULL OR resolution IN ('Done', 'Fixed', 'Duplicate', 'Won''t Do', 'Cannot Reproduce', 'Other')",
            name="ck_task_resolution_allowed",
        ),
        CheckConstraint("parent_id IS NULL OR parent_id != id", name="ck_task_not_own_parent"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default="")
    work_type: Mapped[str] = mapped_column(String(30), default="task", server_default="task")
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True, index=True)
    labels: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    status: Mapped[str] = mapped_column(String, default="backlog", index=True)
    resolution: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    board_origin_status: Mapped[str | None] = mapped_column(String, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    due: Mapped[str | None] = mapped_column(String, nullable=True)
    planned_start: Mapped[str | None] = mapped_column(String, nullable=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assignee_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", name="fk_tasks_assignee_user"), nullable=True, index=True
    )
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
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    field_changes: Mapped[list["TaskFieldChange"]] = relationship(
        back_populates="audit", cascade="all, delete-orphan"
    )


class TaskFieldChange(Base):
    __tablename__ = "task_field_changes"
    __table_args__ = (
        UniqueConstraint("audit_id", "field", "kind"),
        Index("ix_task_field_changes_field_audit", "field", "audit_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audit_logs.id", ondelete="CASCADE"), index=True)
    field: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(30), default="value")
    before_json: Mapped[str] = mapped_column(Text)
    after_json: Mapped[str] = mapped_column(Text)
    audit: Mapped[Audit] = relationship(back_populates="field_changes")


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


class KanbanColumn(Base):
    __tablename__ = "kanban_columns"
    __table_args__ = (
        UniqueConstraint("workflow_order"),
        UniqueConstraint("view_order"),
        CheckConstraint("category IN ('todo', 'in_progress', 'done')", name="ck_kanban_columns_category"),
        CheckConstraint("wip_limit IS NULL OR wip_limit > 0", name="ck_kanban_columns_wip_limit_positive"),
    )
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    category: Mapped[str] = mapped_column(String(20), default="todo", server_default="todo")
    workflow_order: Mapped[int] = mapped_column(Integer)
    view_order: Mapped[int] = mapped_column(Integer)
    wip_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)


class KanbanSavedView(Base):
    __tablename__ = "kanban_saved_views"
    __table_args__ = (UniqueConstraint("user_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    layout: Mapped[str] = mapped_column(String(20), default="board")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    position: Mapped[int] = mapped_column(Integer, default=0)
    shared: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    shared_roles: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    shared_group_ids: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")


class SavedFilter(Base):
    __tablename__ = "saved_filters"
    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_saved_filters_owner_name"),
        Index("ix_saved_filters_shared", "shared"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    query: Mapped[str] = mapped_column(Text)
    shared: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    shared_roles: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    shared_group_ids: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    created_at: Mapped[str] = mapped_column(String, default=now)
    updated_at: Mapped[str] = mapped_column(String, default=now)


class UserGroup(Base):
    __tablename__ = "user_groups"
    __table_args__ = (UniqueConstraint("name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(String, default=now)


class UserGroupMembership(Base):
    __tablename__ = "user_group_memberships"
    __table_args__ = (UniqueConstraint("group_id", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("user_groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(String, default=now)


class TaskWatcher(Base):
    __tablename__ = "task_watchers"
    __table_args__ = (UniqueConstraint("task_id", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[str] = mapped_column(String, default=now)


class InAppNotification(Base):
    __tablename__ = "in_app_notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    source_label: Mapped[str] = mapped_column(String(120), default="", server_default="")
    created_at: Mapped[str] = mapped_column(String, default=now, index=True)
    read_at: Mapped[str | None] = mapped_column(String, nullable=True)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    updated_at: Mapped[str] = mapped_column(String, default=now)


class EmailOutbox(Base):
    __tablename__ = "email_outbox"
    __table_args__ = (
        UniqueConstraint("notification_id", name="uq_email_outbox_notification"),
        CheckConstraint("status IN ('pending', 'sending', 'sent', 'skipped', 'failed')", name="ck_email_outbox_status"),
        CheckConstraint("attempts >= 0", name="ck_email_outbox_attempts"),
        Index("ix_email_outbox_due", "status", "next_attempt_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    notification_id: Mapped[int] = mapped_column(
        ForeignKey("in_app_notifications.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    next_attempt_at: Mapped[str] = mapped_column(String, default=now, index=True)
    updated_at: Mapped[str] = mapped_column(String, default=now)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    __table_args__ = (Index("ix_push_subscriptions_user", "user_id"),)
    endpoint_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    encrypted_payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, default=now)


class PushOutbox(Base):
    __tablename__ = "push_outbox"
    __table_args__ = (
        UniqueConstraint("notification_id", "subscription_hash", name="uq_push_outbox_notice_device"),
        CheckConstraint("status IN ('pending', 'sending', 'sent', 'skipped', 'failed')", name="ck_push_outbox_status"),
        CheckConstraint("attempts >= 0", name="ck_push_outbox_attempts"),
        Index("ix_push_outbox_due", "status", "next_attempt_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    notification_id: Mapped[int] = mapped_column(
        ForeignKey("in_app_notifications.id", ondelete="CASCADE")
    )
    subscription_hash: Mapped[str] = mapped_column(
        ForeignKey("push_subscriptions.endpoint_hash", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    next_attempt_at: Mapped[str] = mapped_column(String, default=now, index=True)
    updated_at: Mapped[str] = mapped_column(String, default=now)


class FilterSubscription(Base):
    __tablename__ = "filter_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_filter_subscription_user_name"),
        CheckConstraint("frequency IN ('daily', 'weekly')", name="ck_filter_subscription_frequency"),
        Index("ix_filter_subscriptions_due", "active", "next_run_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    query: Mapped[str] = mapped_column(Text)
    frequency: Mapped[str] = mapped_column(String(10), default="daily", server_default="daily")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), index=True)
    next_run_at: Mapped[str] = mapped_column(String, index=True)
    last_run_at: Mapped[str | None] = mapped_column(String, nullable=True)
    last_error: Mapped[str] = mapped_column(String(240), default="", server_default="")
    created_at: Mapped[str] = mapped_column(String, default=now)


class FilterSubscriptionMatch(Base):
    __tablename__ = "filter_subscription_matches"
    __table_args__ = (Index("ix_filter_subscription_matches_task", "task_id"),)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("filter_subscriptions.id", ondelete="CASCADE"), primary_key=True
    )
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    matched_at: Mapped[str] = mapped_column(String, default=now)


class Release(Base):
    __tablename__ = "releases"
    __table_args__ = (UniqueConstraint("name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    starts: Mapped[str | None] = mapped_column(String, nullable=True)
    due: Mapped[str | None] = mapped_column(String, nullable=True)
    released_at: Mapped[str | None] = mapped_column(String, nullable=True)
    archived: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), index=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(String, default=now)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version}


class Component(Base):
    __tablename__ = "components"
    __table_args__ = (UniqueConstraint("name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class TaskRelease(Base):
    __tablename__ = "task_releases"
    __table_args__ = (UniqueConstraint("task_id", "release_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    release_id: Mapped[int] = mapped_column(ForeignKey("releases.id"), index=True)
    linked_at: Mapped[str] = mapped_column(String, default=now)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class TaskComponent(Base):
    __tablename__ = "task_components"
    __table_args__ = (UniqueConstraint("task_id", "component_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("components.id"), index=True)
    linked_at: Mapped[str] = mapped_column(String, default=now)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (
        UniqueConstraint("source_task_id", "target_task_id", "link_type"),
        CheckConstraint("source_task_id != target_task_id", name="ck_dependency_not_self"),
        CheckConstraint(
            "link_type IN ('blocks', 'relates', 'duplicates')", name="ck_dependency_link_type"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    source_task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    target_task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    link_type: Mapped[str] = mapped_column(String(20))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(String, default=now)


class ResourceCapacity(Base):
    __tablename__ = "resource_capacity"
    __table_args__ = (
        CheckConstraint(
            "(supplier_id IS NOT NULL AND user_id IS NULL AND group_id IS NULL) OR "
            "(supplier_id IS NULL AND user_id IS NOT NULL AND group_id IS NULL) OR "
            "(supplier_id IS NULL AND user_id IS NULL AND group_id IS NOT NULL)",
            name="ck_capacity_one_resource",
        ),
        CheckConstraint("minutes >= 0", name="ck_capacity_nonnegative"),
        UniqueConstraint("supplier_id", "user_id", "starts", "ends"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id"), nullable=True, index=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("user_groups.id"), nullable=True, index=True)
    group_member_ids: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    starts: Mapped[str] = mapped_column(String)
    ends: Mapped[str] = mapped_column(String)
    minutes: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(Text, default="")
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    leveling_plans: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    leveling_plan_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class WorkflowTransition(Base):
    __tablename__ = "workflow_transitions"
    __table_args__ = (UniqueConstraint("source", "target"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(60), index=True)
    target: Mapped[str] = mapped_column(String(60), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    roles: Mapped[list] = mapped_column(JSON, default=list)
    work_types: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    type_rules: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    required_fields: Mapped[list] = mapped_column(JSON, default=list)
    conditions: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    actions: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[str] = mapped_column(String, default=now)


class AutomationRule(Base):
    __tablename__ = "automation_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    trigger: Mapped[str] = mapped_column(String(40), index=True)
    schedule_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    schedule_frequency: Mapped[str] = mapped_column(String(10), default="daily", server_default="daily")
    schedule_weekdays: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    conditions: Mapped[dict] = mapped_column(JSON, default=dict)
    action: Mapped[str] = mapped_column(String(40))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    actions: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(String, default=now)
    updated_at: Mapped[str] = mapped_column(String, default=now)


class AutomationRun(Base):
    __tablename__ = "automation_runs"
    __table_args__ = (UniqueConstraint("rule_id", "run_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(
        ForeignKey("automation_rules.id", ondelete="CASCADE"), index=True
    )
    run_date: Mapped[str] = mapped_column(String(10))
    completed_at: Mapped[str] = mapped_column(String, default=now)


class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"
    __table_args__ = (UniqueConstraint("user_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    group_by: Mapped[str] = mapped_column(String(30))
    group_by_secondary: Mapped[str | None] = mapped_column(String(30), nullable=True)
    jql: Mapped[str] = mapped_column(Text, default="", server_default="")
    measure: Mapped[str] = mapped_column(String(30), default="count")
    chart: Mapped[str] = mapped_column(String(20), default="bar")
    shared: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    shared_roles: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    shared_group_ids: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    result_columns: Mapped[list] = mapped_column(
        JSON,
        default=lambda: ["key", "summary", "status", "priority", "assignee", "due"],
        server_default='["key","summary","status","priority","assignee","due"]',
    )
    max_results: Mapped[int] = mapped_column(Integer, default=50, server_default="50")
    position: Mapped[int] = mapped_column(Integer, default=0)
    dashboard_id: Mapped[int] = mapped_column(
        ForeignKey("dashboards.id", ondelete="CASCADE"), index=True
    )


class Dashboard(Base):
    __tablename__ = "dashboards"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_dashboards_user_name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    created_at: Mapped[str] = mapped_column(String, default=now)


class DashboardWidgetPosition(Base):
    __tablename__ = "dashboard_widget_positions"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_dashboard_widget_position_nonnegative"),
        Index("ix_dashboard_widget_positions_user_position", "user_id", "position"),
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    widget_id: Mapped[int] = mapped_column(
        ForeignKey("dashboard_widgets.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer)


class DevelopmentEvent(Base):
    __tablename__ = "development_events"
    __table_args__ = (UniqueConstraint("provider", "delivery_id", "task_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    delivery_id: Mapped[str] = mapped_column(String(160))
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(60))
    summary: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000), default="")
    actor: Mapped[str] = mapped_column(String(160), default="")
    occurred_at: Mapped[str | None] = mapped_column(String, nullable=True)
    received_at: Mapped[str] = mapped_column(String, default=now)
    details: Mapped[dict] = mapped_column("metadata", JSON, default=dict, server_default="{}")


class CalendarFeedToken(Base):
    __tablename__ = "calendar_feed_tokens"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[str] = mapped_column(String, default=now)
