import pytest
from datetime import date
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import (
    Audit,
    Attachment,
    Comment,
    Component,
    Hours,
    KanbanColumn,
    Release,
    Role,
    SchemaVersion,
    Sprint,
    Task,
    TaskComponent,
    TaskDependency,
    TaskFieldChange,
    TaskRelease,
    TaskWatcher,
    UserGroup,
    UserGroupMembership,
    Supplier,
    User,
)
from app.query_language import apply_query
from app.services import audit


def test_status_category_jql_filters_and_orders_custom_workflow_columns():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="category-query", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        db.add_all([
            KanbanColumn(key="backlog", title="Backlog", is_system=True, category="todo", workflow_order=0, view_order=0),
            KanbanColumn(key="todo", title="A fazer", is_system=True, category="todo", workflow_order=100, view_order=1),
            KanbanColumn(key="production", title="Em produção", is_system=True, category="in_progress", workflow_order=200, view_order=2),
            KanbanColumn(key="review", title="Em revisão", is_system=True, category="in_progress", workflow_order=300, view_order=3),
            KanbanColumn(key="qa", title="QA", is_system=False, category="in_progress", workflow_order=400, view_order=4),
            KanbanColumn(key="done", title="Concluído", is_system=True, category="done", workflow_order=1000, view_order=5),
        ])
        db.flush()
        tasks = [
            Task(title=status, creator_id=actor.id, status=status)
            for status in ("backlog", "todo", "production", "review", "qa", "done")
        ]
        db.add_all(tasks)
        db.flush()

        todo = db.scalars(apply_query(select(Task), 'statusCategory = "To Do" ORDER BY statusCategory, id'))
        assert list(todo) == tasks[:2]
        progress = db.scalars(apply_query(select(Task), 'statusCategory = "In Progress"'))
        assert set(progress) == set(tasks[2:5])
        done = db.scalars(apply_query(select(Task), 'statusCategory = "Done"'))
        assert list(done) == [tasks[5]]
        selected = db.scalars(apply_query(select(Task), 'statusCategory IN ("To Do", "Done")'))
        assert set(selected) == set(tasks[:2] + [tasks[5]])
        excluded = db.scalars(apply_query(select(Task), 'statusCategory != "In Progress"'))
        assert set(excluded) == set(tasks[:2] + [tasks[5]])
        descending = db.scalars(apply_query(select(Task), "ORDER BY statusCategory DESC, id"))
        assert list(descending) == [tasks[5], *tasks[2:5], *tasks[:2]]

        with pytest.raises(HTTPException):
            apply_query(select(Task), 'statusCategory = "Unknown"')
        with pytest.raises(HTTPException):
            apply_query(select(Task), 'statusCategory ~ "Done"')
    engine.dispose()


def test_jira_resolution_field_filters_persisted_resolution_reasons():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="resolution-query", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.add_all([
            KanbanColumn(key="backlog", title="Backlog", is_system=True, category="todo", workflow_order=0, view_order=0),
            KanbanColumn(key="done", title="Concluído", is_system=True, category="done", workflow_order=1000, view_order=1),
            KanbanColumn(key="released", title="Publicado", is_system=False, category="done", workflow_order=1100, view_order=2),
        ])
        db.flush()
        open_task = Task(title="Aberto", creator_id=actor.id, status="backlog")
        done_task = Task(title="Concluído", creator_id=actor.id, status="done", resolution="Done")
        released_task = Task(title="Publicado", creator_id=actor.id, status="released", resolution="Fixed")
        db.add_all([open_task, done_task, released_task])
        db.flush()

        resolved = db.scalars(apply_query(select(Task), 'resolution = "Done" ORDER BY resolution DESC, id')).all()
        fixed = db.scalars(apply_query(select(Task), 'resolution = "fixed"')).all()
        unresolved = db.scalars(apply_query(select(Task), "resolution IS EMPTY")).all()
        explicitly_resolved = db.scalars(apply_query(select(Task), "resolution IS NOT EMPTY")).all()
        assert resolved == [done_task]
        assert fixed == [released_task]
        assert unresolved == [open_task]
        assert explicitly_resolved == [done_task, released_task]

        with pytest.raises(HTTPException, match="resolution aceita"):
            apply_query(select(Task), "resolution = \"Won't Ship\"")
        with pytest.raises(HTTPException):
            apply_query(select(Task), 'resolution WAS "Done"')
    engine.dispose()


def test_advanced_query_compiles_only_allowlisted_conditions():
    query = apply_query(
        select(Task),
        'status = "review" AND priority <= 5 AND text ~ "revisar" ORDER BY due ASC',
    )
    sql = str(query.compile(compile_kwargs={"literal_binds": True}))
    assert "tasks.status = 'review'" in sql
    assert "tasks.priority <= 5" in sql
    assert "tasks.title LIKE" in sql
    assert "ORDER BY tasks.due ASC" in sql


def test_advanced_query_orders_by_multiple_fields_with_stable_id_tiebreaking():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="sort-user", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        first = Task(title="Primeira", creator_id=actor.id, priority=1, due="2026-11-01")
        second = Task(title="Segunda", creator_id=actor.id, priority=3, due="2026-11-01")
        third = Task(title="Terceira", creator_id=actor.id, priority=4, due="2026-11-02")
        fourth = Task(title="Quarta", creator_id=actor.id, priority=4, due="2026-11-02")
        db.add_all([first, second, third, fourth])
        db.flush()

        query = apply_query(select(Task), "ORDER BY due ASC, priority DESC, id DESC")

        assert db.scalars(query).all() == [second, first, fourth, third]
    engine.dispose()


def test_jira_key_alias_filters_and_orders_by_card_identity():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="key-query", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        first = Task(title="Primeiro", creator_id=actor.id)
        second = Task(title="Segundo", creator_id=actor.id)
        db.add_all([first, second])
        db.flush()

        assert db.scalars(apply_query(select(Task), f'key = "OS-{second.id}"')).all() == [second]
        assert db.scalars(apply_query(select(Task), "key IN (OS-1, OS-2) ORDER BY key DESC")).all() == [second, first]
    engine.dispose()


def test_common_jira_field_aliases_filter_order_and_search_card_history():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="jira-alias-query", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        story = Task(
            title="Resumo compatível",
            creator_id=actor.id,
            work_type="story",
            due="2026-11-10",
        )
        task = Task(title="Outra atividade", creator_id=actor.id, work_type="task")
        db.add_all([story, task])
        db.flush()
        audit(db, actor, "task", story.id, "edited", changes=[{"field": "title", "before": "Rascunho", "after": "Resumo compatível"}])
        db.commit()

        assert db.scalars(apply_query(select(Task), 'summary ~ "compatível"')).all() == [story]
        assert db.scalars(apply_query(select(Task), 'issuetype = story')).all() == [story]
        assert db.scalars(apply_query(select(Task), 'dueDate = "2026-11-10" ORDER BY summary')).all() == [story]
        assert db.scalars(apply_query(select(Task), 'summary WAS "Rascunho"')).all() == [story]
        assert db.scalars(apply_query(select(Task), 'summary CHANGED TO "Resumo compatível"')).all() == [story]
    engine.dispose()


def test_resolutiondate_uses_latest_audited_completion_and_clears_when_reopened():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="resolution-query", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        earlier = Task(title="Concluída ontem", creator_id=actor.id, status="done")
        resolved_today = Task(title="Concluída hoje", creator_id=actor.id, status="done")
        reopened = Task(title="Reaberta", creator_id=actor.id, status="review")
        done_without_history = Task(title="Concluída sem auditoria", creator_id=actor.id, status="done")
        db.add_all([earlier, resolved_today, reopened, done_without_history])
        db.flush()

        for task, timestamp, origin in (
            (earlier, "2026-11-06T23:55:00+00:00", "review"),
            (resolved_today, "2026-11-07T10:15:00+00:00", "review"),
            (reopened, "2026-11-06T12:00:00+00:00", "review"),
        ):
            audit(
                db,
                actor,
                "task",
                task.id,
                "status_changed",
                timestamp=timestamp,
                origin=origin,
                destination="done",
            )
        audit(
            db,
            actor,
            "task",
            reopened.id,
            "status_changed",
            timestamp="2026-11-07T11:00:00+00:00",
            origin="done",
            destination="review",
        )
        db.flush()

        assert db.scalars(apply_query(select(Task), 'resolutiondate = "2026-11-07"')).all() == [resolved_today]
        assert db.scalars(apply_query(select(Task), 'resolutiondate <= "2026-11-07" ORDER BY resolutiondate')).all() == [earlier, resolved_today]
        assert db.scalars(apply_query(select(Task), 'resolutiondate > "2026-11-06"')).all() == [resolved_today]
        assert set(db.scalars(apply_query(select(Task), "resolved IS EMPTY"))) == {reopened, done_without_history}
        assert db.scalars(apply_query(select(Task), "resolution_date IS NOT EMPTY ORDER BY resolutiondate DESC")).all() == [resolved_today, earlier]
    engine.dispose()


def test_jql_filters_schedule_and_hour_values_with_numeric_and_date_types():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="planning-query", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        planned = Task(
            title="Card planejado", creator_id=actor.id, planned_start="2026-11-01",
            due="2026-11-30", estimated_minutes=300, used_minutes=120,
        )
        unscheduled = Task(title="Sem agenda", creator_id=actor.id, estimated_minutes=90)
        db.add_all([planned, unscheduled])
        db.flush()

        query = apply_query(
            select(Task),
            'planned_start <= "2026-11-07" AND planned_end >= "2026-11-30" '
            'AND estimated_minutes >= 300 AND used_minutes = 120 ORDER BY planned_start DESC',
        )
        assert db.scalars(query).all() == [planned]
        assert db.scalars(apply_query(select(Task), "planned_start IS EMPTY")).all() == [unscheduled]
        relative = apply_query(
            select(Task), "planned_start <= startOfDay() AND estimated_minutes > 0",
            current_date=date(2026, 11, 7),
        )
        assert db.scalars(relative).all() == [planned]
    engine.dispose()


@pytest.mark.parametrize(
    "source",
    [
        "password = secret",
        "approval = unknown",
        "priority >= high",
        'text ~ "unclosed',
        "status = backlog OR",
        "(status = backlog OR status = todo",
        "priority = 2 ORDER BY priority ASC, priority DESC",
        "priority = 2 ORDER BY password DESC",
        "attachments = true",
        "attachments in (1, 2)",
    ],
)
def test_invalid_or_unsupported_queries_are_rejected(source):
    with pytest.raises(HTTPException):
        apply_query(select(Task), source)


def test_query_functions_resolve_current_user_and_sprint_state_safely():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="current-person", password_hash="hash", role="admin", grants=[])
        other = User(username="other-person", password_hash="hash", role="admin", grants=[])
        db.add_all([actor, other])
        db.flush()
        active = Sprint(name="Ativa", objective="", starts="2026-11-01", ends="2026-11-14", state="active", owner_id=actor.id)
        closed = Sprint(name="Encerrada", objective="", starts="2026-10-01", ends="2026-10-14", state="closed", owner_id=actor.id)
        planned = Sprint(name="Planejada", objective="", starts="2026-12-01", ends="2026-12-14", state="planned", owner_id=actor.id)
        db.add_all([active, closed, planned])
        db.flush()
        mine = Task(title="Minha tarefa", creator_id=actor.id, assignee_user_id=actor.id, sprint_id=active.id)
        theirs = Task(title="Tarefa de outra pessoa", creator_id=other.id, assignee_user_id=other.id, sprint_id=closed.id)
        planned_task = Task(title="Tarefa planejada", creator_id=actor.id, sprint_id=planned.id)
        db.add_all([mine, theirs, planned_task])
        db.flush()

        current_user_query = apply_query(
            select(Task), "assignee = currentUser()", actor_user_id=actor.id
        )
        created_by_current_user = apply_query(
            select(Task), "creator = currentUser()", actor_user_id=actor.id
        )
        open_sprint_query = apply_query(select(Task), "sprint in openSprints()")
        closed_sprint_query = apply_query(select(Task), "sprint = closedSprints()")
        assert db.scalars(current_user_query).all() == [mine]
        assert db.scalars(created_by_current_user).all() == [mine, planned_task]
        assert db.scalars(open_sprint_query).all() == [mine]
        assert db.scalars(closed_sprint_query).all() == [theirs]

        with pytest.raises(HTTPException):
            apply_query(select(Task), "assignee = currentUser()")
        with pytest.raises(HTTPException):
            apply_query(select(Task), "status = currentUser()", actor_user_id=actor.id)
    engine.dispose()


def test_watcher_jql_filters_are_correlated_and_supplier_scope_is_self_only():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Role(id="admin"), Role(id="supplier")])
        db.flush()
        admin = User(username="watch-admin", password_hash="hash", role="admin", grants=[])
        another = User(username="watch-other", password_hash="hash", role="admin", grants=[])
        vendor = User(username="watch-vendor", password_hash="hash", role="supplier", grants=[])
        db.add_all([admin, another, vendor])
        db.flush()
        watched_by_admin = Task(title="Admin acompanha", creator_id=admin.id)
        watched_by_other = Task(title="Outra pessoa acompanha", creator_id=admin.id)
        unwatched = Task(title="Sem observador", creator_id=admin.id)
        db.add_all([watched_by_admin, watched_by_other, unwatched])
        db.flush()
        db.add_all([
            TaskWatcher(task_id=watched_by_admin.id, user_id=admin.id),
            TaskWatcher(task_id=watched_by_other.id, user_id=another.id),
        ])
        db.flush()

        mine = apply_query(
            select(Task), "watcher = currentUser()", actor_user_id=admin.id, actor_role="admin"
        )
        selected_watchers = apply_query(
            select(Task), f"watcher in ({admin.id}, {another.id})", actor_role="admin"
        )
        without_watchers = apply_query(select(Task), "watcher IS EMPTY", actor_role="admin")
        self_scoped_supplier_query = apply_query(
            select(Task), "watcher = currentUser()", actor_user_id=vendor.id, actor_role="supplier"
        )

        assert db.scalars(mine).all() == [watched_by_admin]
        assert db.scalars(selected_watchers).all() == [watched_by_admin, watched_by_other]
        assert db.scalars(without_watchers).all() == [unwatched]
        assert db.scalars(self_scoped_supplier_query).all() == []

        with pytest.raises(HTTPException) as explicit_supplier_filter:
            apply_query(select(Task), f"watcher = {admin.id}", actor_role="supplier")
        assert explicit_supplier_filter.value.status_code == 403
        with pytest.raises(HTTPException) as supplier_empty_filter:
            apply_query(select(Task), "watcher IS EMPTY", actor_role="supplier")
        assert supplier_empty_filter.value.status_code == 403
        with pytest.raises(HTTPException):
            apply_query(select(Task), "watcher = currentUser()", actor_role="admin")
    engine.dispose()


def test_jql_user_fields_accept_usernames_ids_aliases_and_mixed_lists():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Role(id="admin"), Role(id="internal")])
        db.flush()
        author = User(username="reporter-one", password_hash="hash", role="admin", grants=[])
        assignee = User(username="delivery.person", password_hash="hash", role="internal", grants=[])
        other = User(username="other-person", password_hash="hash", role="internal", grants=[])
        db.add_all([author, assignee, other])
        db.flush()
        assigned = Task(title="Atribuída", creator_id=author.id, assignee_user_id=assignee.id)
        reported = Task(title="Reportada", creator_id=author.id, assignee_user_id=other.id)
        other_report = Task(title="Outro autor", creator_id=other.id, assignee_user_id=assignee.id)
        db.add_all([assigned, reported, other_report])
        db.flush()
        db.add_all([
            TaskWatcher(task_id=assigned.id, user_id=assignee.id),
            TaskWatcher(task_id=reported.id, user_id=other.id),
        ])
        db.flush()

        by_username = apply_query(select(Task), 'assignee = "delivery.person"')
        by_alias = apply_query(select(Task), 'reporter = "reporter-one"')
        mixed = apply_query(
            select(Task), f'assignee IN ("delivery.person", {other.id})'
        )
        excluding = apply_query(select(Task), 'creator != "reporter-one"')
        watched = apply_query(select(Task), 'watcher = "delivery.person"')
        missing_user = apply_query(select(Task), 'assignee = "unknown-user"')

        assert db.scalars(by_username).all() == [assigned, other_report]
        assert db.scalars(by_alias).all() == [assigned, reported]
        assert db.scalars(mixed).all() == [assigned, reported, other_report]
        assert db.scalars(excluding).all() == [other_report]
        assert db.scalars(watched).all() == [assigned]
        assert db.scalars(missing_user).all() == []
    engine.dispose()


def test_members_of_jql_filters_assignees_and_watchers_by_active_internal_group():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Role(id="admin"), Role(id="internal"), Role(id="supplier")])
        db.flush()
        admin = User(username="group-admin", password_hash="hash", role="admin", grants=[])
        member = User(username="group-member", password_hash="hash", role="internal", grants=[])
        outsider = User(username="group-outsider", password_hash="hash", role="internal", grants=[])
        vendor = User(username="group-vendor", password_hash="hash", role="supplier", grants=[])
        db.add_all([admin, member, outsider, vendor])
        db.flush()
        group = UserGroup(name="Produto", description="", active=True, author_id=admin.id)
        db.add(group)
        db.flush()
        db.add(UserGroupMembership(group_id=group.id, user_id=member.id, author_id=admin.id))
        assigned_member = Task(title="Responsável do grupo", creator_id=admin.id, assignee_user_id=member.id)
        assigned_outsider = Task(title="Responsável externo ao grupo", creator_id=admin.id, assignee_user_id=outsider.id)
        created_by_member = Task(title="Criado por membro do grupo", creator_id=member.id, assignee_user_id=outsider.id)
        db.add_all([assigned_member, assigned_outsider, created_by_member])
        db.flush()
        db.add(TaskWatcher(task_id=assigned_member.id, user_id=member.id))
        db.flush()

        by_name = apply_query(
            select(Task), 'assignee in membersOf("Produto")', actor_role="admin"
        )
        by_id = apply_query(
            select(Task), f"assignee in membersOf(id:{group.id})", actor_role="admin"
        )
        excluded = apply_query(
            select(Task), 'assignee not in membersOf("Produto")', actor_role="admin"
        )
        watched = apply_query(
            select(Task), 'watcher in membersOf("Produto")', actor_role="admin"
        )
        reported_by_group = apply_query(
            select(Task), 'reporter in membersOf("Produto")', actor_role="admin"
        )
        assert db.scalars(by_name).all() == [assigned_member]
        assert db.scalars(by_id).all() == [assigned_member]
        assert db.scalars(excluded).all() == [assigned_outsider, created_by_member]
        assert db.scalars(watched).all() == [assigned_member]
        assert db.scalars(reported_by_group).all() == [created_by_member]

        group.active = False
        db.flush()
        assert db.scalars(by_name).all() == []
        with pytest.raises(HTTPException) as supplier_filter:
            apply_query(
                select(Task), 'assignee in membersOf("Produto")', actor_role="supplier"
            )
        assert supplier_filter.value.status_code == 403
    engine.dispose()


def test_relative_jql_date_functions_use_utc_boundaries_and_offsets():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="date-filter", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        before = Task(title="Antes", creator_id=actor.id, due="2026-11-01", created_at="2026-11-06T23:59:59+00:00")
        during = Task(title="Dentro", creator_id=actor.id, due="2026-11-07", created_at="2026-11-07T13:00:00+00:00")
        after = Task(title="Depois", creator_id=actor.id, due="2026-11-09", created_at="2026-11-08T00:00:00+00:00")
        db.add_all([before, during, after])
        db.flush()

        due_week = apply_query(
            select(Task),
            "due >= startOfWeek() AND due <= endOfWeek()",
            current_date=date(2026, 11, 7),
        )
        created_today = apply_query(
            select(Task),
            "created >= startOfDay() AND created < startOfDay()+1d",
            current_date=date(2026, 11, 7),
        )
        next_month = apply_query(
            select(Task), "due >= startOfMonth()+1M", current_date=date(2026, 10, 31)
        )
        assert db.scalars(due_week).all() == [during]
        assert db.scalars(created_today).all() == [during]
        assert db.scalars(next_month).all() == [before, during, after]
    engine.dispose()


def test_updated_jql_uses_latest_task_audit_or_created_timestamp_and_sorts():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="updated-filter", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        changed_today = Task(title="Atualizado hoje", creator_id=actor.id, created_at="2026-11-01T09:00:00+00:00")
        created_only = Task(title="Sem edição", creator_id=actor.id, created_at="2026-11-02T09:00:00+00:00")
        changed_yesterday = Task(title="Atualizado ontem", creator_id=actor.id, created_at="2026-11-03T09:00:00+00:00")
        db.add_all([changed_today, created_only, changed_yesterday])
        db.flush()
        db.add_all([
            Audit(
                actor_id=actor.id,
                entity="task",
                entity_id=changed_today.id,
                action="comment_added",
                details={},
                created_at="2026-11-07T14:00:00+00:00",
            ),
            Audit(
                actor_id=actor.id,
                entity="task",
                entity_id=changed_yesterday.id,
                action="status_changed",
                details={},
                created_at="2026-11-06T14:00:00+00:00",
            ),
        ])
        db.flush()

        updated_today = apply_query(select(Task), 'updated = "2026-11-07"')
        recent = apply_query(
            select(Task), "updated >= startOfDay()", current_date=date(2026, 11, 7)
        )
        dates = apply_query(select(Task), 'updated IN ("2026-11-02", "2026-11-06")')
        ordered = apply_query(select(Task), "ORDER BY updated DESC")

        assert db.scalars(updated_today).all() == [changed_today]
        assert db.scalars(recent).all() == [changed_today]
        assert db.scalars(dates).all() == [created_only, changed_yesterday]
        assert db.scalars(ordered).all() == [changed_today, changed_yesterday, created_only]
    engine.dispose()


def test_updated_by_jql_matches_audit_actor_and_bounded_utc_date_ranges():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Role(id="admin"), Role(id="internal"), Role(id="supplier")])
        db.flush()
        actor = User(username="updater-owner", password_hash="hash", role="admin", grants=[])
        editor = User(username="updater-editor", password_hash="hash", role="internal", grants=[])
        vendor = User(username="updater-vendor", password_hash="hash", role="supplier", grants=[])
        db.add_all([actor, editor, vendor])
        db.flush()
        recent = Task(title="Alterado hoje", creator_id=actor.id)
        yesterday = Task(title="Alterado ontem", creator_id=actor.id)
        editor_update = Task(title="Alterado pelo editor", creator_id=actor.id)
        supplier_update = Task(title="Alterado pelo fornecedor", creator_id=actor.id)
        untouched = Task(title="Sem auditoria", creator_id=actor.id)
        db.add_all([recent, yesterday, editor_update, supplier_update, untouched])
        db.flush()
        db.add_all([
            Audit(actor_id=actor.id, entity="task", entity_id=recent.id, action="status_changed", details={}, created_at="2026-11-07T15:00:00+00:00"),
            Audit(actor_id=actor.id, entity="task", entity_id=yesterday.id, action="comment_added", details={}, created_at="2026-11-06T15:00:00+00:00"),
            Audit(actor_id=editor.id, entity="task", entity_id=editor_update.id, action="task_updated", details={}, created_at="2026-11-07T10:00:00+00:00"),
            Audit(actor_id=vendor.id, entity="task", entity_id=supplier_update.id, action="comment_added", details={}, created_at="2026-11-07T11:00:00+00:00"),
        ])
        db.flush()

        self_updates = apply_query(
            select(Task), "issue in updatedBy(currentUser())", actor_user_id=actor.id
        )
        default_user_updates = apply_query(
            select(Task), "issue in updatedBy()", actor_user_id=actor.id
        )
        editor_window = apply_query(
            select(Task),
            'issue in updatedBy("updater-editor", "2026-11-07", "2026-11-07")',
        )
        recent_window = apply_query(
            select(Task),
            'issue in updatedBy(currentUser(), "-1d", "2026-11-07")',
            actor_user_id=actor.id,
            current_date=date(2026, 11, 7),
        )
        supplier_self = apply_query(
            select(Task),
            "issue in updatedBy(currentUser())",
            actor_user_id=vendor.id,
            actor_role="supplier",
        )
        assert db.scalars(self_updates).all() == [recent, yesterday]
        assert db.scalars(default_user_updates).all() == [recent, yesterday]
        assert db.scalars(editor_window).all() == [editor_update]
        assert db.scalars(recent_window).all() == [recent, yesterday]
        assert db.scalars(supplier_self).all() == [supplier_update]

        with pytest.raises(HTTPException) as blocked_supplier_identity:
            apply_query(
                select(Task), 'issue in updatedBy("updater-editor")', actor_role="supplier"
            )
        assert blocked_supplier_identity.value.status_code == 403
        with pytest.raises(HTTPException):
            apply_query(select(Task), "status in updatedBy(currentUser())", actor_user_id=actor.id)
        with pytest.raises(HTTPException):
            apply_query(
                select(Task),
                'issue in updatedBy(currentUser(), "2026-11-07", "2026-11-06")',
                actor_user_id=actor.id,
            )
    engine.dispose()


def test_worklog_author_jql_matches_hour_versions_and_limits_supplier_identity():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Role(id="admin"), Role(id="internal"), Role(id="supplier")])
        db.flush()
        owner = User(username="hours-owner", password_hash="hash", role="admin", grants=[])
        editor = User(username="hours-editor", password_hash="hash", role="internal", grants=[])
        vendor = User(username="hours-vendor", password_hash="hash", role="supplier", grants=[])
        db.add_all([owner, editor, vendor])
        db.flush()
        owner_task = Task(title="Horas do admin", creator_id=owner.id)
        editor_task = Task(title="Horas do editor", creator_id=owner.id)
        vendor_task = Task(title="Horas do fornecedor", creator_id=owner.id)
        no_hours = Task(title="Sem apontamento", creator_id=owner.id)
        db.add_all([owner_task, editor_task, vendor_task, no_hours])
        db.flush()
        db.add_all([
            Hours(task_id=owner_task.id, version=1, estimated_minutes=60, used_minutes=30, author_id=owner.id, created_at="2026-11-07T10:00:00+00:00", comment="Revisão do relatório"),
            Hours(task_id=owner_task.id, version=2, estimated_minutes=60, used_minutes=35, author_id=owner.id, created_at="2026-11-07T11:00:00+00:00", comment="Ajuste revisado"),
            Hours(task_id=editor_task.id, version=1, estimated_minutes=60, used_minutes=45, author_id=editor.id, created_at="2026-11-06T10:00:00+00:00", comment="Validação técnica"),
            Hours(task_id=vendor_task.id, version=1, estimated_minutes=60, used_minutes=50, author_id=vendor.id, created_at="2026-11-07T12:00:00+00:00", comment="Teste funcional"),
        ])
        db.flush()

        assert db.scalars(apply_query(select(Task), "worklogAuthor = currentUser()", actor_user_id=owner.id)).all() == [owner_task]
        assert db.scalars(apply_query(select(Task), 'worklogAuthor = "hours-editor"')).all() == [editor_task]
        assert db.scalars(apply_query(select(Task), "worklogAuthor IN (currentUser(), hours-editor)", actor_user_id=owner.id)).all() == [owner_task, editor_task]
        assert db.scalars(apply_query(select(Task), "worklogAuthor != currentUser()", actor_user_id=owner.id)).all() == [editor_task, vendor_task, no_hours]
        assert db.scalars(apply_query(select(Task), 'worklogDate = "2026-11-07"')).all() == [owner_task, vendor_task]
        assert db.scalars(apply_query(select(Task), 'worklogDate != "2026-11-07"')).all() == [editor_task, no_hours]
        assert db.scalars(apply_query(select(Task), 'worklogDate IN ("2026-11-06", "2026-11-07")')).all() == [owner_task, editor_task, vendor_task]
        assert db.scalars(apply_query(select(Task), "worklogDate >= startOfWeek()", current_date=date(2026, 11, 7))).all() == [owner_task, editor_task, vendor_task]
        assert db.scalars(apply_query(select(Task), 'worklogComment ~ "relatório"')).all() == [owner_task]
        assert db.scalars(apply_query(select(Task), 'worklogComment ~ "validação"')).all() == [editor_task]
        assert db.scalars(apply_query(
            select(Task), 'worklogComment ~ "funcional"', actor_user_id=vendor.id, actor_role="supplier"
        )).all() == [vendor_task]
        assert db.scalars(apply_query(
            select(Task), 'worklogComment ~ "relatório"', actor_user_id=vendor.id, actor_role="supplier"
        )).all() == []
        assert db.scalars(apply_query(
            select(Task), "worklogAuthor = currentUser()", actor_user_id=vendor.id, actor_role="supplier"
        )).all() == [vendor_task]
        with pytest.raises(HTTPException) as blocked_supplier_identity:
            apply_query(select(Task), 'worklogAuthor = "hours-editor"', actor_role="supplier")
        assert blocked_supplier_identity.value.status_code == 403
        with pytest.raises(HTTPException):
            apply_query(select(Task), "worklogAuthor ~ editor", actor_user_id=owner.id)
        with pytest.raises(HTTPException):
            apply_query(select(Task), "worklogAuthor = currentUser()")
        with pytest.raises(HTTPException):
            apply_query(select(Task), "worklogComment = relatório")
        with pytest.raises(HTTPException):
            apply_query(select(Task), 'worklogComment ~ "funcional"', actor_role="supplier")
    engine.dispose()


def test_comment_author_jql_supports_lists_and_restricts_supplier_to_self():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Role(id="admin"), Role(id="internal"), Role(id="supplier")])
        db.flush()
        owner = User(username="comment-owner", password_hash="hash", role="admin", grants=[])
        editor = User(username="comment-editor", password_hash="hash", role="internal", grants=[])
        vendor = User(username="comment-vendor", password_hash="hash", role="supplier", grants=[])
        db.add_all([owner, editor, vendor])
        db.flush()
        owner_task = Task(title="Comentado pelo admin", creator_id=owner.id)
        editor_task = Task(title="Comentado pelo editor", creator_id=owner.id)
        vendor_task = Task(title="Comentado pelo fornecedor", creator_id=owner.id)
        empty_task = Task(title="Sem comentários", creator_id=owner.id)
        db.add_all([owner_task, editor_task, vendor_task, empty_task])
        db.flush()
        db.add_all([
            Comment(task_id=owner_task.id, body="Comentário do admin", author_id=owner.id, created_at="2026-11-07T10:00:00+00:00"),
            Comment(task_id=editor_task.id, body="Comentário interno", author_id=editor.id, created_at="2026-11-06T10:00:00+00:00"),
            Comment(task_id=vendor_task.id, body="Comentário do fornecedor", author_id=vendor.id, created_at="2026-11-07T12:00:00+00:00"),
        ])
        db.flush()

        assert db.scalars(apply_query(
            select(Task), "commentAuthor = currentUser()", actor_user_id=owner.id
        )).all() == [owner_task]
        assert db.scalars(apply_query(
            select(Task), "commentAuthor IN (currentUser(), comment-editor)", actor_user_id=owner.id
        )).all() == [owner_task, editor_task]
        assert db.scalars(apply_query(
            select(Task), "commentAuthor != currentUser()", actor_user_id=owner.id
        )).all() == [editor_task, vendor_task, empty_task]
        assert db.scalars(apply_query(select(Task), 'commentDate = "2026-11-07"')).all() == [owner_task, vendor_task]
        assert db.scalars(apply_query(
            select(Task), 'commentDate IN ("2026-11-06", "2026-11-07")'
        )).all() == [owner_task, editor_task, vendor_task]
        assert db.scalars(apply_query(
            select(Task), "commentDate >= startOfWeek()", current_date=date(2026, 11, 7)
        )).all() == [owner_task, editor_task, vendor_task]
        assert db.scalars(apply_query(
            select(Task), "commentAuthor = currentUser()", actor_user_id=vendor.id,
            actor_role="supplier",
        )).all() == [vendor_task]
        with pytest.raises(HTTPException) as blocked_supplier_identity:
            apply_query(select(Task), 'commentAuthor = "comment-editor"', actor_role="supplier")
        assert blocked_supplier_identity.value.status_code == 403
        with pytest.raises(HTTPException):
            apply_query(select(Task), "commentAuthor = currentUser()")
        with pytest.raises(HTTPException):
            apply_query(select(Task), "commentAuthor ~ user", actor_user_id=owner.id)
        with pytest.raises(HTTPException):
            apply_query(select(Task), "commentDate ~ yesterday")
    engine.dispose()


def test_advanced_query_supports_or_parentheses_and_not_in_safely():
    query = apply_query(
        select(Task),
        '(status = "review" OR status = "done") AND priority NOT IN (1, 2) ORDER BY due DESC',
    )
    sql = str(query.compile(compile_kwargs={"literal_binds": True}))
    assert " OR " in sql
    assert " AND " in sql
    assert "NOT IN (1, 2)" in sql
    assert "ORDER BY tasks.due DESC" in sql


def test_boolean_keywords_inside_quoted_text_are_not_parsed_as_operators():
    query = apply_query(select(Task), 'text ~ "bug OR task AND release"')
    sql = str(query.compile(compile_kwargs={"literal_binds": True}))
    assert "bug OR task AND release" in sql


def test_text_search_includes_title_description_and_custom_card_values():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="text-search", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        title_match = Task(title="Farol estratégico", creator_id=actor.id)
        description_match = Task(title="Entrega", description="Revisar contrato", creator_id=actor.id)
        custom_match = Task(title="Card", creator_id=actor.id)
        comment_match = Task(title="Tarefa comentada", creator_id=actor.id)
        db.add_all([title_match, description_match, custom_match, comment_match])
        db.flush()
        db.add(Comment(task_id=comment_match.id, body="Validar checklist de deploy", author_id=actor.id))
        db.add(
            SchemaVersion(
                task_id=custom_match.id,
                version=1,
                fields=[{"id": "area", "type": "text"}],
                values={"area": "Acessibilidade"},
                author_id=actor.id,
            )
        )
        db.flush()

        def find(term):
            return set(db.scalars(apply_query(select(Task), f'text ~ "{term}"')))

        assert find("Farol") == {title_match}
        assert find("contrato") == {description_match}
        assert find("Acessibilidade") == {custom_match}
        assert find("checklist") == {comment_match}
        comment_query = apply_query(select(Task), 'comment ~ "checklist"')
        assert db.scalars(comment_query).all() == [comment_match]
    engine.dispose()


def test_historical_status_query_filters_by_change_actor_and_utc_date():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Role(id="admin"), Role(id="internal")])
        db.flush()
        actor = User(username="pedro", password_hash="hash", role="admin", grants=[])
        other = User(username="other", password_hash="hash", role="internal", grants=[])
        db.add_all([actor, other])
        db.flush()
        matching = Task(title="Transição encontrada", creator_id=actor.id, status="production")
        non_matching = Task(title="Outra transição", creator_id=other.id, status="review")
        db.add_all([matching, non_matching])
        db.flush()
        db.add_all([
            Audit(
                actor_id=actor.id,
                entity="task",
                entity_id=matching.id,
                action="status_changed",
                details={"origin": "backlog", "destination": "production"},
                created_at="2026-11-06T12:00:00+00:00",
            ),
            Audit(
                actor_id=other.id,
                entity="task",
                entity_id=non_matching.id,
                action="status_changed",
                details={"origin": "todo", "destination": "review"},
                created_at="2026-11-06T12:00:00+00:00",
            ),
        ])
        db.flush()
        status_events = list(db.scalars(select(Audit).where(Audit.action == "status_changed")))
        db.add_all(
            TaskFieldChange(
                audit_id=row.id,
                field="status",
                kind="value",
                before_json=f'"{row.details["origin"]}"',
                after_json=f'"{row.details["destination"]}"',
            )
            for row in status_events
        )
        db.flush()

        query = apply_query(
            select(Task),
            'status CHANGED FROM backlog TO production BY pedro AFTER "2026-11-05" BEFORE "2026-11-07"',
        )
        assert db.scalars(query).all() == [matching]
    engine.dispose()


def test_historical_query_supports_native_field_changes_and_empty_values():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="pedro", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        changed_task = Task(
            title="Prazo alterado",
            creator_id=actor.id,
            priority=5,
            due="2026-12-01",
        )
        removed_due_task = Task(title="Prazo removido", creator_id=actor.id, due=None)
        db.add_all([changed_task, removed_due_task])
        db.flush()
        audit(
            db,
            actor,
            "task",
            changed_task.id,
            "edited",
            timestamp="2026-11-06T12:00:00+00:00",
            changes=[{"field": "priority", "before": 1, "after": 5}],
        )
        audit(
            db,
            actor,
            "task",
            removed_due_task.id,
            "edited",
            timestamp="2026-11-06T13:00:00+00:00",
            changes=[{"field": "due", "before": "2026-12-01", "after": None}],
        )
        db.flush()

        priority_query = apply_query(
            select(Task), 'priority CHANGED FROM 1 TO 5 BY pedro AFTER "2026-11-05"'
        )
        was_query = apply_query(
            select(Task), 'priority WAS IN (1, 5) BY pedro AFTER "2026-11-05"'
        )
        was_not_query = apply_query(select(Task), "priority WAS NOT 99")
        was_not_in_query = apply_query(select(Task), "priority WAS NOT IN (1, 5)")
        was_not_scoped = apply_query(
            select(Task),
            'priority WAS NOT 99 BY pedro DURING ("2026-11-06", "2026-11-06")',
        )
        was_not_other_actor = apply_query(
            select(Task), 'priority WAS NOT 99 BY nobody'
        )
        due_query = apply_query(select(Task), "due CHANGED TO EMPTY")
        due_was_query = apply_query(select(Task), "due WAS EMPTY")
        during_changed = apply_query(
            select(Task), 'priority CHANGED BY pedro DURING ("2026-11-06", "2026-11-06")'
        )
        during_was = apply_query(
            select(Task), 'priority WAS IN (1, 5) DURING ("2026-11-06", "2026-11-06")'
        )
        outside_period = apply_query(
            select(Task), 'priority CHANGED DURING ("2026-11-07", "2026-11-08")'
        )
        instant_window = apply_query(
            select(Task),
            'priority CHANGED BY pedro DURING ("2026-11-06T11:59:59+00:00", "2026-11-06T12:00:01+00:00")',
        )
        assert db.scalars(priority_query).all() == [changed_task]
        assert db.scalars(was_query).all() == [changed_task]
        assert db.scalars(was_not_query).all() == [changed_task]
        assert db.scalars(was_not_in_query).all() == []
        assert db.scalars(was_not_scoped).all() == [changed_task]
        assert db.scalars(was_not_other_actor).all() == []
        assert db.scalars(due_query).all() == [removed_due_task]
        assert db.scalars(due_was_query).all() == [removed_due_task]
        assert db.scalars(during_changed).all() == [changed_task]
        assert db.scalars(during_was).all() == [changed_task]
        assert db.scalars(outside_period).all() == []
        assert db.scalars(instant_window).all() == [changed_task]
    engine.dispose()


def test_historical_query_supports_individual_custom_field_values():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="pedro", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        task = Task(title="Área alterada", creator_id=actor.id)
        db.add(task)
        db.flush()
        audit(
            db,
            actor,
            "task",
            task.id,
            "values_versioned",
            changes=[
                {
                    "field": "area",
                    "kind": "value",
                    "before": "Operações",
                    "after": "Produtos",
                }
            ],
        )
        db.flush()
        changed = apply_query(select(Task), 'field_area CHANGED FROM "Operações" TO "Produtos" BY pedro')
        was = apply_query(select(Task), 'field_area WAS IN ("Operações", "Produtos")')
        was_not = apply_query(select(Task), 'field_area WAS NOT "Não cadastrado"')
        assert db.scalars(changed).all() == [task]
        assert db.scalars(was).all() == [task]
        assert db.scalars(was_not).all() == [task]
    engine.dispose()


def test_admin_can_query_individual_custom_field_configuration_history():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="pedro", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        task = Task(title="Configuração alterada", creator_id=actor.id)
        db.add(task)
        db.flush()
        audit(
            db,
            actor,
            "task",
            task.id,
            "schema_versioned",
            changes=[
                {
                    "field": "area",
                    "kind": "configuration",
                    "before": {"id": "area", "label": "Área", "type": "text", "required": False, "options": ["Legado"]},
                    "after": {"id": "area", "label": "Área responsável", "type": "text", "required": True, "options": ["Legado", "Novo"]},
                }
            ],
        )
        audit(
            db,
            actor,
            "task",
            task.id,
            "schema_versioned",
            changes=[
                {
                    "field": "new_field",
                    "kind": "configuration",
                    "before": None,
                    "after": {"id": "new_field", "label": "Novo campo", "type": "text"},
                }
            ],
        )
        db.flush()
        changed = apply_query(
            select(Task),
            'field_config_area_label CHANGED FROM "Área" TO "Área responsável" BY pedro',
        )
        required = apply_query(
            select(Task), "field_config_area_required CHANGED FROM false TO true"
        )
        was = apply_query(select(Task), 'field_config_area_label WAS "Área responsável"')
        options = apply_query(
            select(Task), 'field_config_area_options CHANGED FROM ["Legado"] TO ["Legado","Novo"]'
        )
        added = apply_query(
            select(Task), 'field_config_new_field_label CHANGED FROM EMPTY TO "Novo campo"'
        )
        assert db.scalars(changed).all() == [task]
        assert db.scalars(required).all() == [task]
        assert db.scalars(was).all() == [task]
        assert db.scalars(options).all() == [task]
        assert db.scalars(added).all() == [task]
        with pytest.raises(HTTPException) as error:
            apply_query(
                select(Task), 'field_config_area_label CHANGED TO "Área responsável"',
                allow_configuration_history=False,
            )
        assert error.value.status_code == 403
    engine.dispose()


@pytest.mark.parametrize("source", [
    "status CHANGED BY",
    'status CHANGED AFTER "yesterday"',
    "label CHANGED TO production",
])
def test_invalid_historical_query_forms_are_rejected(source):
    with pytest.raises(HTTPException):
        apply_query(select(Task), source)


def test_advanced_query_filters_hierarchy_assignee_release_and_component_links():
    query = apply_query(
        select(Task),
        "parent IN (10, 11) AND assignee = 4 AND release = 3 AND component NOT IN (7, 8)",
    )
    sql = str(query.compile(compile_kwargs={"literal_binds": True}))
    assert "tasks.parent_id IN (10, 11)" in sql
    assert "tasks.assignee_user_id = 4" in sql
    assert "task_releases" in sql
    assert "task_components" in sql
    assert "NOT" in sql


def test_fixversion_jql_resolves_exact_release_names_and_keeps_id_support():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="fixversion-query", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        named = Task(title="Release com nome", creator_id=actor.id)
        other = Task(title="Outra release", creator_id=actor.id)
        no_release = Task(title="Sem release", creator_id=actor.id)
        db.add_all([named, other, no_release])
        db.flush()
        first = Release(name="Entrega, etapa 1", author_id=actor.id)
        second = Release(name="Entrega 2", author_id=actor.id)
        db.add_all([first, second])
        db.flush()
        db.add_all([
            TaskRelease(task_id=named.id, release_id=first.id, author_id=actor.id),
            TaskRelease(task_id=other.id, release_id=second.id, author_id=actor.id),
        ])
        db.flush()

        def find(query):
            return set(db.scalars(apply_query(select(Task), query)))

        assert find('fixVersion = "Entrega, etapa 1"') == {named}
        assert find('fixversion IN ("Entrega, etapa 1", "Entrega 2")') == {named, other}
        assert find(f"release = {first.id}") == {named}
        assert find('fixVersion NOT IN ("Entrega, etapa 1")') == {other, no_release}
        assert find('fixVersion = "Versão inexistente"') == set()
    engine.dispose()


def test_sprint_jql_resolves_exact_names_and_preserves_sprint_functions():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="sprint-name-query", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        first = Sprint(
            name="Entrega novembro", objective="", starts="2026-11-01", ends="2026-11-14",
            state="planned", owner_id=actor.id,
        )
        second = Sprint(
            name="Entrega dezembro", objective="", starts="2026-12-01", ends="2026-12-14",
            state="active", owner_id=actor.id,
        )
        db.add_all([first, second])
        db.flush()
        first_task = Task(title="Sprint um", creator_id=actor.id, sprint_id=first.id)
        second_task = Task(title="Sprint dois", creator_id=actor.id, sprint_id=second.id)
        unplanned = Task(title="Sem sprint", creator_id=actor.id)
        db.add_all([first_task, second_task, unplanned])
        db.flush()

        def find(query):
            return set(db.scalars(apply_query(select(Task), query)))

        assert find('sprint = "Entrega novembro"') == {first_task}
        assert find('sprint IN ("Entrega novembro", "Entrega dezembro")') == {first_task, second_task}
        assert find(f"sprint = {first.id}") == {first_task}
        assert find("sprint IN openSprints()") == {second_task}
        assert find('sprint NOT IN ("Entrega novembro")') == {second_task, unplanned}
    engine.dispose()


def test_linked_issues_jql_filters_dependency_edges_bidirectionally():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="linked-query", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        blocker = Task(title="Bloqueador", creator_id=actor.id)
        blocked = Task(title="Bloqueado", creator_id=actor.id)
        related = Task(title="Relacionado", creator_id=actor.id)
        unrelated = Task(title="Sem vínculo", creator_id=actor.id)
        db.add_all([blocker, blocked, related, unrelated])
        db.flush()
        db.add_all([
            TaskDependency(
                source_task_id=blocker.id,
                target_task_id=blocked.id,
                link_type="blocks",
                author_id=actor.id,
            ),
            TaskDependency(
                source_task_id=blocked.id,
                target_task_id=related.id,
                link_type="relates",
                author_id=actor.id,
            ),
        ])
        db.flush()

        def find(query):
            return set(db.scalars(apply_query(select(Task), query)))

        assert find('issue IN linkedIssues("OS-1")') == {blocked}
        assert find('id IN linkedIssues(2, blocks)') == {blocker}
        assert find("issue IN linkedIssues(2)") == {blocker, related}
        assert find("issue NOT IN linkedIssues(1)") == {blocker, related, unrelated}
        with pytest.raises(HTTPException):
            apply_query(select(Task), 'status IN linkedIssues("OS-1")')
        with pytest.raises(HTTPException):
            apply_query(select(Task), 'issue IN linkedIssues("OS-1", "unknown")')
        with pytest.raises(HTTPException) as denied:
            apply_query(
                select(Task),
                'issue IN linkedIssues("OS-1")',
                actor_role="supplier",
            )
        assert denied.value.status_code == 403
    engine.dispose()


def test_advanced_query_supports_is_empty_for_nullable_and_related_fields():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="pedro", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        empty = Task(title="Sem planejamento", creator_id=actor.id, labels=[])
        filled = Task(title="Planejada", creator_id=actor.id, due="2026-12-01", labels=["ux"])
        db.add_all([empty, filled])
        db.flush()
        supplier = Supplier(name="Fornecedor de teste", function="Design")
        sprint = Sprint(
            name="Sprint de teste", objective="", starts="2026-11-01", ends="2026-11-14", owner_id=actor.id
        )
        db.add_all([supplier, sprint])
        db.flush()
        filled.supplier_id = supplier.id
        filled.sprint_id = sprint.id
        filled.parent_id = empty.id
        filled.assignee_user_id = actor.id
        release = Release(name="R1", author_id=actor.id)
        component = Component(name="API", author_id=actor.id)
        db.add_all([release, component])
        db.flush()
        db.add_all([
            TaskRelease(task_id=filled.id, release_id=release.id, author_id=actor.id),
            TaskComponent(task_id=filled.id, component_id=component.id, author_id=actor.id),
            Attachment(
                task_id=filled.id,
                name="evidencia.pdf",
                media_type="application/pdf",
                content=b"%PDF-test",
                size=9,
                sha256="a" * 64,
                author_id=actor.id,
            ),
        ])
        db.flush()

        for field in (
            "due", "supplier", "sprint", "parent", "assignee", "release", "component", "label", "attachments"
        ):
            query = apply_query(select(Task), f"{field} IS EMPTY")
            assert db.scalars(query).all() == [empty]
            query = apply_query(select(Task), f"{field} IS NOT EMPTY")
            assert db.scalars(query).all() == [filled]
    engine.dispose()


@pytest.mark.parametrize("source", ["status IS EMPTY", "password IS NOT EMPTY"])
def test_empty_query_rejects_nonnullable_or_unknown_fields(source):
    with pytest.raises(HTTPException):
        apply_query(select(Task), source)


@pytest.mark.parametrize(
    "source",
    [
        'status CHANGED DURING ("2026-11-08", "2026-11-07")',
        'status WAS todo DURING ("invalid", "2026-11-07")',
        'status CHANGED AFTER "2026-11-01" DURING ("2026-11-02", "2026-11-03")',
    ],
)
def test_historical_during_requires_a_valid_exclusive_date_range(source):
    with pytest.raises(HTTPException):
        apply_query(select(Task), source)


@pytest.mark.parametrize(
    "source",
    [
        "parent = 10",
        "parent IS EMPTY",
        "parent WAS 10",
        "parent CHANGED",
    ],
)
def test_supplier_cannot_query_task_hierarchy(source):
    with pytest.raises(HTTPException) as denied:
        apply_query(select(Task), source, actor_role="supplier")

    assert denied.value.status_code == 403
