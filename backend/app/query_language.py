"""Small, allowlisted issue query language; user input never becomes SQL."""

import json
import re
import calendar
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import String, and_, case, cast, func, or_, select

from .models import (
    Audit,
    Attachment,
    Comment,
    Component,
    Hours,
    KanbanColumn,
    Release,
    SchemaVersion,
    Sprint,
    Task,
    TaskComponent,
    TaskDependency,
    TaskFieldChange,
    TaskRelease,
    TaskWatcher,
    User,
    UserGroup,
    UserGroupMembership,
)
from .services import fail


TERM = re.compile(
    r"^\s*([a-z_]+)\s*(=|!=|~|>=|<=|>|<|NOT\s+IN|IN)\s*(.*?)\s*$",
    re.IGNORECASE,
)
EMPTY = re.compile(r"^\s*([a-z_]+)\s+IS\s+(NOT\s+)?EMPTY\s*$", re.IGNORECASE)
ORDER_FIELD = r"[a-z_]+(?:\s+(?:ASC|DESC))?"
ORDER = re.compile(
    rf"(?:^|\s+)ORDER\s+BY\s+(?P<fields>{ORDER_FIELD}(?:\s*,\s*{ORDER_FIELD}){{0,4}})\s*$",
    re.IGNORECASE,
)
HISTORY_VALUE = r'(\[[^\]\r\n]{1,120}\]|"[^"\r\n]{1,120}"|\'[^\'\r\n]{1,120}\'|[^\s(),]{1,120})'
HISTORY_VALUE_ATOM = r'(?:\[[^\]\r\n]{1,120}\]|"[^"\r\n]{1,120}"|\'[^\'\r\n]{1,120}\'|[^\s(),]{1,120})'
HISTORY_PERIOD = rf'\(\s*{HISTORY_VALUE_ATOM}\s*,\s*{HISTORY_VALUE_ATOM}\s*\)'
HISTORY_FIELD = r"([a-z_]+|field_[a-zA-Z][a-zA-Z0-9_]{0,79})"
FIELD_CHANGED = re.compile(
    rf"^\s*{HISTORY_FIELD}\s+CHANGED"
    rf"(?:\s+FROM\s+({HISTORY_VALUE}))?"
    rf"(?:\s+TO\s+({HISTORY_VALUE}))?"
    rf"(?:\s+BY\s+({HISTORY_VALUE}))?"
    rf"(?:\s+AFTER\s+({HISTORY_VALUE}))?"
    rf"(?:\s+BEFORE\s+({HISTORY_VALUE}))?"
    rf"(?:\s+DURING\s+({HISTORY_PERIOD}))?\s*$",
    re.IGNORECASE,
)
FIELD_WAS = re.compile(
    rf"^\s*(?P<field>{HISTORY_FIELD})\s+WAS\s+(?P<negated>NOT\s+)?(?:IN\s*)?"
    rf"(?P<values>\([^()\r\n]{{1,500}}\)|{HISTORY_VALUE})"
    rf"(?:\s+BY\s+(?P<actor>{HISTORY_VALUE}))?"
    rf"(?:\s+AFTER\s+(?P<after>{HISTORY_VALUE}))?"
    rf"(?:\s+BEFORE\s+(?P<before>{HISTORY_VALUE}))?"
    rf"(?:\s+DURING\s+(?P<during>{HISTORY_PERIOD}))?\s*$",
    re.IGNORECASE,
)
FIELDS = {
    "status": "status",
    "statuscategory": "__status_category",
    "priority": "priority",
    "type": "work_type",
    "work_type": "work_type",
    "issuetype": "work_type",
    "issue_type": "work_type",
    "supplier": "supplier_id",
    "supplier_id": "supplier_id",
    "sprint": "sprint_id",
    "sprint_id": "sprint_id",
    "parent": "parent_id",
    "parent_id": "parent_id",
    "assignee": "assignee_user_id",
    "assignee_id": "assignee_user_id",
    "creator": "creator_id",
    "creator_id": "creator_id",
    "reporter": "creator_id",
    "watcher": "__watcher",
    "release": "__release_id",
    "release_id": "__release_id",
    "fixversion": "__release_id",
    "fix_version": "__release_id",
    "component": "__component_id",
    "component_id": "__component_id",
    "issue": "__issue_id",
    "key": "__issue_id",
    "issuekey": "__issue_id",
    "id": "__issue_id",
    "approval": "approval",
    "due": "due",
    "duedate": "due",
    "due_date": "due",
    "planned_end": "due",
    "planned_start": "planned_start",
    "estimated_minutes": "estimated_minutes",
    "used_minutes": "used_minutes",
    "created": "created_at",
    "updated": "__updated_at",
    "updated_date": "__updated_at",
    "resolutiondate": "__resolution_date",
    "resolution_date": "__resolution_date",
    "resolved": "__resolution_date",
    "resolution": "__resolution",
    "title": "title",
    "summary": "title",
    "description": "description",
    "comment": "__comment",
    "commentauthor": "__comment_author",
    "commentdate": "__comment_date",
    "text": "__text",
    "label": "labels",
    "attachments": "__attachments",
    "worklogauthor": "__worklog_author",
    "worklog_author": "__worklog_author",
    "worklogdate": "__worklog_date",
    "worklog_date": "__worklog_date",
    "worklogcomment": "__worklog_comment",
    "worklog_comment": "__worklog_comment",
}
APPROVALS = {"pending", "approved", "rejected", "resubmitted"}
WORK_TYPES = {"epic", "story", "task", "bug", "subtask"}
RESOLUTIONS = {"done", "fixed", "duplicate", "won't do", "cannot reproduce", "other"}


def _value(raw):
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
        return raw[1:-1]
    if not raw:
        fail("Consulta avançada sem valor.")
    return raw


def _list_values(raw, *, maximum=30):
    """Parse a bounded comma-separated list without splitting quoted names."""
    if not raw.startswith("(") or not raw.endswith(")"):
        fail("Use IN (valor1, valor2) para consultar listas.")
    source = raw[1:-1]
    values, start, quote = [], 0, None
    for index, char in enumerate(source):
        if quote:
            if char == quote and (index == 0 or source[index - 1] != "\\"):
                quote = None
        elif char in {'"', "'"}:
            quote = char
        elif char == ",":
            item = source[start:index].strip()
            if not item:
                fail("A lista IN contém um valor vazio.")
            values.append(_value(item))
            start = index + 1
    final = source[start:].strip()
    if quote or not final:
        fail("A lista IN precisa conter valores válidos e aspas fechadas.")
    values.append(_value(final))
    if len(values) > maximum:
        fail(f"A lista IN precisa conter de 1 a {maximum} valores.")
    return values


def _status_category_clause(raw):
    identity = _value(raw).strip().casefold().replace("-", " ")
    categories = {
        "to do": "todo", "todo": "todo", "a fazer": "todo", "backlog": "todo",
        "in progress": "in_progress", "inprogress": "in_progress", "em andamento": "in_progress",
        "done": "done", "concluido": "done", "concluído": "done",
    }
    category = categories.get(identity)
    if category is None:
        fail('statusCategory aceita "To Do", "In Progress" ou "Done".')
    column_keys = select(KanbanColumn.key).where(KanbanColumn.category == category)
    return Task.status.in_(column_keys)


def _status_category_rank():
    return case(
        (_status_category_clause('"Done"'), 2),
        (_status_category_clause('"In Progress"'), 1),
        else_=0,
    )


def _split_boolean(source, keyword):
    pieces, start, quote, depth = [], 0, None, 0
    index = 0
    while index < len(source):
        char = source[index]
        if quote:
            if char == quote and (index == 0 or source[index - 1] != "\\"):
                quote = None
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
            index += 1
            continue
        if char == "(":
            depth += 1
            index += 1
            continue
        if char == ")":
            depth -= 1
            if depth < 0:
                fail("Parênteses não correspondem na consulta avançada.")
            index += 1
            continue
        end = index + len(keyword)
        if (
            depth == 0
            and source[index:end].upper() == keyword
            and (index == 0 or not (source[index - 1].isalnum() or source[index - 1] == "_"))
            and (end == len(source) or not (source[end].isalnum() or source[end] == "_"))
        ):
            piece = source[start:index].strip()
            if not piece:
                fail("Consulta incompleta ao combinar condições.")
            pieces.append(piece)
            start = end
            index = end
            continue
        index += 1
    if quote or depth:
        fail("Aspas ou parênteses não foram fechados na consulta avançada.")
    final_piece = source[start:].strip()
    if not final_piece:
        fail("Consulta incompleta ao combinar condições.")
    pieces.append(final_piece)
    return pieces


def _has_outer_parentheses(source):
    if not (source.startswith("(") and source.endswith(")")):
        return False
    quote, depth = None, 0
    for index, char in enumerate(source):
        if quote:
            if char == quote and (index == 0 or source[index - 1] != "\\"):
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0 and index != len(source) - 1:
                return False
    return depth == 0 and quote is None


def _expression(source, *, actor_user_id=None, actor_role=None, current_date=None):
    source = source.strip()
    while _has_outer_parentheses(source):
        source = source[1:-1].strip()
    groups = _split_boolean(source, "OR")
    if len(groups) > 1:
        return or_(*(_expression(group, actor_user_id=actor_user_id, actor_role=actor_role, current_date=current_date) for group in groups))
    terms = _split_boolean(source, "AND")
    if len(terms) > 1:
        return and_(*(_expression(term, actor_user_id=actor_user_id, actor_role=actor_role, current_date=current_date) for term in terms))
    return _condition(source, actor_user_id=actor_user_id, actor_role=actor_role, current_date=current_date)


def _condition(piece, *, actor_user_id=None, actor_role=None, current_date=None):
    empty = EMPTY.match(piece)
    if empty:
        field = FIELDS.get(empty.group(1).lower())
        if not field:
            fail("Campo não permitido para consulta de vazio.")
        if field == "parent_id" and actor_role == "supplier":
            fail("Filtros de hierarquia estão disponíveis apenas para usuários internos.", 403, "FORBIDDEN")
        if field == "__watcher" and actor_role == "supplier":
            fail("Filtros de observadores estão restritos ao próprio usuário fornecedor.", 403, "FORBIDDEN")
        is_not_empty = bool(empty.group(2))
        if field in {"__release_id", "__component_id"}:
            exists = select(TaskRelease.id if field == "__release_id" else TaskComponent.id)
            if field == "__release_id":
                exists = exists.where(TaskRelease.task_id == Task.id)
            else:
                exists = exists.where(TaskComponent.task_id == Task.id)
            condition = exists.exists()
            return condition if is_not_empty else ~condition
        if field == "labels":
            # JSON equality is handled by SQLAlchemy's dialect-aware serializer.
            condition = Task.labels != []
            return condition if is_not_empty else ~condition
        if field == "__watcher":
            condition = select(TaskWatcher.id).where(TaskWatcher.task_id == Task.id).exists()
            return condition if is_not_empty else ~condition
        if field == "__attachments":
            condition = select(Attachment.id).where(Attachment.task_id == Task.id).exists()
            return condition if is_not_empty else ~condition
        if field == "__resolution_date":
            condition = _resolution_date_column().is_not(None)
            return condition if is_not_empty else ~condition
        if field == "__resolution":
            condition = _resolution_column().is_not(None)
            return condition if is_not_empty else ~condition
        if field == "__worklog_author":
            fail("worklogAuthor não aceita IS EMPTY nem IS NOT EMPTY.")
        if field == "__worklog_comment":
            fail("worklogComment aceita apenas o operador ~.")
        if field not in {
            "supplier_id", "sprint_id", "parent_id", "assignee_user_id", "due", "planned_start"
        }:
            fail("IS EMPTY está disponível para supplier, sprint, parent, assignee, due/planned_end, planned_start, resolutiondate, release, component e label.")
        condition = getattr(Task, field).is_not(None)
        return condition if is_not_empty else ~condition

    was = FIELD_WAS.match(piece)
    if was:
        source_field = was.group("field")
        field = FIELDS.get(source_field.lower())
        custom = field is None and source_field.lower().startswith("field_")
        configuration = custom and source_field[6:].lower().startswith("config_")
        if custom:
            field = source_field[6:]
        if field == "parent_id" and actor_role == "supplier":
            fail("Filtros de hierarquia estão disponíveis apenas para usuários internos.", 403, "FORBIDDEN")
        if field not in {
            "status",
            "priority",
            "work_type",
            "supplier_id",
            "sprint_id",
            "parent_id",
            "assignee_user_id",
            "approval",
            "due",
            "title",
        } and not custom:
            fail("Histórico WAS disponível para status, priority/issuetype, supplier, sprint, parent, assignee, approval, due e title/summary.")
        values = _custom_history_values(was.group("values")) if custom else _history_values(field, was.group("values"))
        if not values:
            fail("WAS IN precisa conter valores válidos.")
        conditions = [
            Audit.entity == "task",
            Audit.entity_id == Task.id,
            TaskFieldChange.audit_id == Audit.id,
            TaskFieldChange.field == field,
            TaskFieldChange.kind == ("configuration_property" if configuration else "value") if custom else True,
        ]
        negated = bool(was.group("negated"))
        actor_raw, after_raw, before_raw, during_raw = (
            was.group("actor"),
            was.group("after"),
            was.group("before"),
            was.group("during"),
        )
        if during_raw and (after_raw or before_raw):
            fail("Use DURING sozinho ou combine AFTER com BEFORE.")
        if actor_raw:
            username = _value(actor_raw)
            if not username or len(username) > 120:
                fail("BY precisa identificar uma conta válida.")
            history_query = select(TaskFieldChange.id).join(Audit).join(
                User, User.id == Audit.actor_id
            ).where(*conditions, User.username == username)
        else:
            history_query = select(TaskFieldChange.id).join(Audit).where(*conditions)
        if after_raw:
            boundary, inclusive = _history_boundary(after_raw, after=True)
            history_query = history_query.where(
                Audit.created_at >= boundary if inclusive else Audit.created_at > boundary
            )
        if before_raw:
            boundary, inclusive = _history_boundary(before_raw, after=False)
            history_query = history_query.where(
                Audit.created_at <= boundary if inclusive else Audit.created_at < boundary
            )
        if during_raw:
            starts_at, ends_at = _history_period(during_raw)
            history_query = history_query.where(
                Audit.created_at >= starts_at,
                Audit.created_at <= ends_at,
            )
        matching_history = history_query.where(
            or_(TaskFieldChange.before_json.in_(values), TaskFieldChange.after_json.in_(values))
        )
        if negated:
            # A negative historical condition needs evidence of history in the
            # selected scope; records without such history are not inferred.
            return history_query.exists() & ~matching_history.exists()
        return matching_history.exists()

    changed = FIELD_CHANGED.match(piece)
    if changed:
        source_field, _, from_raw, _, to_raw, _, actor_raw, _, after_raw, _, before_raw, during_raw = changed.groups()
        field = FIELDS.get(source_field.lower())
        custom = field is None and source_field.lower().startswith("field_")
        configuration = custom and source_field[6:].lower().startswith("config_")
        if custom:
            field = source_field[6:]
        if field == "parent_id" and actor_role == "supplier":
            fail("Filtros de hierarquia estão disponíveis apenas para usuários internos.", 403, "FORBIDDEN")
        if field not in {
            "status",
            "priority",
            "work_type",
            "supplier_id",
            "sprint_id",
            "parent_id",
            "assignee_user_id",
            "approval",
            "due",
            "title",
        } and not custom:
            fail("Histórico CHANGED disponível para status, priority/issuetype, supplier, sprint, parent, assignee, approval, due e title/summary.")
        conditions = [
            Audit.entity == "task",
            Audit.entity_id == Task.id,
            TaskFieldChange.audit_id == Audit.id,
            TaskFieldChange.field == field,
        ]
        if custom:
            conditions.append(TaskFieldChange.kind == ("configuration_property" if configuration else "value"))
        if from_raw:
            value = _custom_history_json(from_raw) if custom else _history_json(field, _value(from_raw))
            conditions.append(TaskFieldChange.before_json == value)
        if to_raw:
            value = _custom_history_json(to_raw) if custom else _history_json(field, _value(to_raw))
            conditions.append(TaskFieldChange.after_json == value)
        if actor_raw:
            username = _value(actor_raw)
            if not username or len(username) > 120:
                fail("BY precisa identificar uma conta válida.")
            history_query = select(TaskFieldChange.id).join(Audit).join(User, User.id == Audit.actor_id).where(
                *conditions, User.username == username
            )
        else:
            history_query = select(TaskFieldChange.id).join(Audit).where(*conditions)
        if after_raw:
            boundary, inclusive = _history_boundary(after_raw, after=True)
            column = Audit.created_at >= boundary if inclusive else Audit.created_at > boundary
            history_query = history_query.where(column)
        if before_raw:
            boundary, inclusive = _history_boundary(before_raw, after=False)
            column = Audit.created_at <= boundary if inclusive else Audit.created_at < boundary
            history_query = history_query.where(column)
        if during_raw:
            if after_raw or before_raw:
                fail("Use DURING sozinho ou combine AFTER com BEFORE.")
            starts_at, ends_at = _history_period(during_raw)
            history_query = history_query.where(
                Audit.created_at >= starts_at,
                Audit.created_at <= ends_at,
            )
        return history_query.exists()

    match = TERM.match(piece)
    if not match:
        fail("Consulta inválida. Use campo operador valor e combine condições com AND ou OR.")
    source_field, operator, raw = match.groups()
    field = FIELDS.get(source_field.lower())
    if not field:
        fail(
            "Campo não permitido. Disponíveis: status, statusCategory, priority, type/issuetype, supplier, sprint, parent, assignee, creator/reporter, watcher, approval, due/dueDate, planned_end, planned_start, resolution/resolutiondate/resolved, estimated_minutes, used_minutes, created, updated, title/summary, description, text, comment, commentAuthor, commentDate, label, attachments, worklogAuthor, worklogDate, worklogComment, release e component."
        )
    if field == "parent_id" and actor_role == "supplier":
        fail("Filtros de hierarquia estão disponíveis apenas para usuários internos.", 403, "FORBIDDEN")
    operator = re.sub(r"\s+", " ", operator.upper())
    if field == "__status_category":
        if operator in {"IN", "NOT IN"}:
            if not raw.startswith("(") or not raw.endswith(")"):
                fail('Use statusCategory IN ("To Do", "In Progress").')
            values = [_value(item).strip() for item in raw[1:-1].split(",") if item.strip()]
            if not values or len(values) > 3:
                fail("statusCategory IN precisa conter de 1 a 3 categorias.")
            matching = or_(*(_status_category_clause(value) for value in values))
            return ~matching if operator == "NOT IN" else matching
        if operator not in {"=", "!="}:
            fail("statusCategory aceita apenas =, !=, IN e NOT IN.")
        matching = _status_category_clause(raw)
        return ~matching if operator == "!=" else matching
    column = (
        _updated_column()
        if field == "__updated_at"
        else Task.id
        if field == "__issue_id"
        else _resolution_column()
        if field == "__resolution"
        else _resolution_date_column()
        if field == "__resolution_date"
        else getattr(Task, field)
        if not field.startswith("__")
        else None
    )
    if field == "__attachments":
        fail("attachments aceita apenas IS EMPTY e IS NOT EMPTY.")
    if field == "__worklog_author":
        if operator not in {"=", "!=", "IN", "NOT IN"}:
            fail("worklogAuthor aceita apenas =, !=, IN e NOT IN.")
        if operator in {"IN", "NOT IN"}:
            if not raw.startswith("(") or not raw.endswith(")"):
                fail("Use worklogAuthor IN (usuario1, usuario2).")
            identities = [_value(item).strip() for item in raw[1:-1].split(",") if item.strip()]
        else:
            identities = [_value(raw).strip()]
        if not identities or len(identities) > 30:
            fail("worklogAuthor precisa conter de 1 a 30 usuários.")
        user_ids = []
        for identity in identities:
            if re.fullmatch(r"(?i)currentUser\(\)", identity):
                if actor_user_id is None:
                    fail("worklogAuthor = currentUser() exige usuário autenticado.")
                user_ids.append(actor_user_id)
            else:
                if actor_role == "supplier":
                    fail("Fornecedores só podem pesquisar apontamentos da própria conta.", 403, "FORBIDDEN")
                user_ids.append(select(User.id).where(User.username == identity).scalar_subquery())
        matching_worklog = select(Hours.id).where(
            Hours.task_id == Task.id,
            Hours.author_id.in_(user_ids),
        ).exists()
        return matching_worklog if operator in {"=", "IN"} else ~matching_worklog
    if field == "__comment_author":
        if operator not in {"=", "!=", "IN", "NOT IN"}:
            fail("commentAuthor aceita apenas =, !=, IN e NOT IN.")
        if operator in {"IN", "NOT IN"}:
            if not raw.startswith("(") or not raw.endswith(")"):
                fail("Use commentAuthor IN (usuario1, usuario2).")
            identities = [_value(item).strip() for item in raw[1:-1].split(",") if item.strip()]
        else:
            identities = [_value(raw).strip()]
        if not identities or len(identities) > 30:
            fail("commentAuthor precisa conter de 1 a 30 usuários.")
        user_ids = []
        for identity in identities:
            if re.fullmatch(r"(?i)currentUser\(\)", identity):
                if actor_user_id is None:
                    fail("commentAuthor = currentUser() exige usuário autenticado.")
                user_ids.append(actor_user_id)
            else:
                if actor_role == "supplier":
                    fail("Fornecedores só podem pesquisar comentários da própria conta.", 403, "FORBIDDEN")
                user_ids.append(select(User.id).where(User.username == identity).scalar_subquery())
        matching_comment = select(Comment.id).where(
            Comment.task_id == Task.id,
            Comment.author_id.in_(user_ids),
        ).exists()
        return matching_comment if operator in {"=", "IN"} else ~matching_comment
    if field == "__worklog_date":
        if operator in {"IN", "NOT IN"}:
            if not raw.startswith("(") or not raw.endswith(")"):
                fail("Use worklogDate IN (data1, data2).")
            values = [_value(item).strip() for item in raw[1:-1].split(",") if item.strip()]
            if not values or len(values) > 30:
                fail("worklogDate IN precisa conter de 1 a 30 datas.")
            matches = [_activity_date_match(Hours, item, "=", current_date=current_date) for item in values]
            return or_(*matches) if operator == "IN" else and_(*(~match for match in matches))
        if operator not in {"=", "!=", ">", ">=", "<", "<="}:
            fail("worklogDate aceita comparações e IN/NOT IN.")
        return _worklog_date_match(raw, operator, current_date=current_date)
    if field == "__comment_date":
        if operator in {"IN", "NOT IN"}:
            if not raw.startswith("(") or not raw.endswith(")"):
                fail("Use commentDate IN (data1, data2).")
            values = [_value(item).strip() for item in raw[1:-1].split(",") if item.strip()]
            if not values or len(values) > 30:
                fail("commentDate IN precisa conter de 1 a 30 datas.")
            matches = [_activity_date_match(Comment, item, "=", current_date=current_date) for item in values]
            return or_(*matches) if operator == "IN" else and_(*(~match for match in matches))
        if operator not in {"=", "!=", ">", ">=", "<", "<="}:
            fail("commentDate aceita comparações e IN/NOT IN.")
        return _activity_date_match(Comment, raw, operator, current_date=current_date)
    if field == "__worklog_comment":
        if operator != "~":
            fail("worklogComment aceita apenas o operador ~.")
        term = str(_value(raw))
        matching_comment = select(Hours.id).where(
            Hours.task_id == Task.id,
            Hours.comment.is_not(None),
            Hours.comment.contains(term, autoescape=True),
        )
        if actor_role == "supplier":
            if actor_user_id is None:
                fail("worklogComment exige usuário autenticado.")
            matching_comment = matching_comment.where(Hours.author_id == actor_user_id)
        matching_comment = matching_comment.exists()
        return matching_comment
    if field == "__watcher" and actor_role == "supplier" and not re.fullmatch(
        r"(?i)currentUser\(\)", raw.strip()
    ):
        fail("Fornecedores só podem filtrar os próprios observadores com currentUser().", 403, "FORBIDDEN")
    if field in {"__text", "__comment"} and operator != "~":
        fail("Os campos text e comment aceitam apenas o operador ~.")
    linked = re.fullmatch(
        r"(?is)linkedIssues\(\s*(?P<identity>\"[^\"\r\n]{1,100}\"|'[^'\r\n]{1,100}'|OS[-_]\d{1,10}|\d{1,10})\s*"
        r"(?:,\s*(?P<kind>\"(?:blocks|relates|duplicates)\"|'(?:blocks|relates|duplicates)'|(?:blocks|relates|duplicates))\s*)?\)",
        raw.strip(),
    )
    if linked:
        if actor_role == "supplier":
            fail("A pesquisa de vínculos entre cards está disponível apenas para usuários internos.", 403, "FORBIDDEN")
        if field != "__issue_id" or operator not in {"IN", "NOT IN", "=", "!="}:
            fail("linkedIssues() só pode filtrar issue/issuekey/id com IN, NOT IN, = ou !=.")
        reference = _task_identity(linked.group("identity"))
        link_kind = _value(linked.group("kind")) if linked.group("kind") else None
        conditions = [
            or_(
                (TaskDependency.source_task_id == reference)
                & (TaskDependency.target_task_id == Task.id),
                (TaskDependency.target_task_id == reference)
                & (TaskDependency.source_task_id == Task.id),
            )
        ]
        if link_kind:
            conditions.append(TaskDependency.link_type == link_kind.lower())
        related = select(TaskDependency.id).where(*conditions).exists()
        return ~related if operator in {"NOT IN", "!="} else related
    updated_by = re.fullmatch(
        r"(?is)updatedBy\(\s*(?P<user>currentUser\(\)|\"[^\"\r\n]{1,120}\"|'[^'\r\n]{1,120}'|[^\s(),]{1,120})?"
        r"(?:\s*,\s*(?P<after>\"[^\"\r\n]{1,30}\"|'[^'\r\n]{1,30}'|[^\s(),]{1,30})"
        r"(?:\s*,\s*(?P<before>\"[^\"\r\n]{1,30}\"|'[^'\r\n]{1,30}'|[^\s(),]{1,30}))?)?\s*\)",
        raw.strip(),
    )
    if updated_by:
        if actor_role == "supplier" and not re.fullmatch(
            r"(?i)currentUser\(\)", updated_by.group("user").strip()
        ):
            fail("Fornecedores só podem pesquisar atualizações feitas pela própria conta.", 403, "FORBIDDEN")
        if field != "__issue_id" or operator not in {"IN", "NOT IN"}:
            fail("updatedBy() só pode ser usado com IN ou NOT IN no campo issue/id.")
        identity_raw = (updated_by.group("user") or "currentUser()").strip()
        if re.fullmatch(r"(?i)currentUser\(\)", identity_raw):
            if actor_user_id is None:
                fail("updatedBy(currentUser()) exige usuário autenticado.")
            actor_condition = Audit.actor_id == actor_user_id
        else:
            username = _value(identity_raw)
            actor_condition = Audit.actor_id.in_(select(User.id).where(User.username == username))
        updated_audit = select(Audit.id).where(
            Audit.entity == "task",
            Audit.entity_id == Task.id,
            actor_condition,
        )
        after_raw, before_raw = updated_by.group("after"), updated_by.group("before")
        if before_raw and not after_raw:
            fail("updatedBy() exige dateFrom antes de dateTo.")
        if after_raw:
            after = _updated_by_boundary(after_raw, current_date=current_date, end=False)
            updated_audit = updated_audit.where(Audit.created_at >= after)
        if before_raw:
            before = _updated_by_boundary(before_raw, current_date=current_date, end=True)
            if before < after:
                fail("dateTo de updatedBy() deve ser igual ou posterior a dateFrom.")
            updated_audit = updated_audit.where(Audit.created_at <= before)
        matching = updated_audit.exists()
        return matching if operator == "IN" else ~matching
    members = re.fullmatch(
        r"(?is)membersOf\(\s*(?P<identity>\"[^\"\r\n]{1,100}\"|'[^'\r\n]{1,100}'|id:\d{1,10}|\d{1,10})\s*\)",
        raw.strip(),
    )
    if members:
        if actor_role == "supplier":
            fail("Filtros por grupos estão disponíveis apenas para usuários internos.", 403, "FORBIDDEN")
        if field not in {"assignee_user_id", "creator_id", "__watcher"} or operator not in {"IN", "NOT IN"}:
            fail("membersOf() só pode ser usado com IN ou NOT IN em assignee, creator ou watcher.")
        identity = _value(members.group("identity")).strip()
        member_query = select(UserGroupMembership.user_id).join(
            UserGroup, UserGroup.id == UserGroupMembership.group_id
        ).join(User, User.id == UserGroupMembership.user_id).where(
            UserGroup.active.is_(True),
            User.active.is_(True),
            User.role != "supplier",
        )
        group_id = identity.removeprefix("id:")
        if group_id.isdigit():
            member_query = member_query.where(UserGroup.id == int(group_id))
        else:
            member_query = member_query.where(UserGroup.name.ilike(identity))
        if field in {"assignee_user_id", "creator_id"}:
            condition = column.in_(member_query)
        else:
            condition = select(TaskWatcher.id).where(
                TaskWatcher.task_id == Task.id,
                TaskWatcher.user_id.in_(member_query),
            ).exists()
        return condition if operator == "IN" else ~condition
    function = re.fullmatch(r"(?i)(currentUser|openSprints|closedSprints)\(\)", raw.strip())
    if function:
        name = function.group(1).lower()
        if name == "currentuser":
            if field not in {"assignee_user_id", "creator_id", "__watcher"} or actor_user_id is None:
                fail("currentUser() só pode ser usado em assignee, creator ou watcher e exige usuário autenticado.")
            if field == "__watcher":
                condition = _watcher_exists(actor_user_id)
                if operator in {"=", "IN"}:
                    return condition
                if operator in {"!=", "NOT IN"}:
                    return ~condition
                fail("currentUser() aceita apenas =, !=, IN e NOT IN em assignee ou watcher.")
            resolved = actor_user_id
        else:
            if field != "sprint_id":
                fail(f"{function.group(1)}() só pode ser usado no campo sprint.")
            sprint_state = "active" if name == "opensprints" else "closed"
            resolved = select(Sprint.id).where(
                Sprint.state == sprint_state,
                Sprint.archived.is_(False),
            )
            condition = column.in_(resolved)
            if operator in {"=", "IN"}:
                return condition
            if operator in {"!=", "NOT IN"}:
                return ~condition
            fail("Funções de sprint aceitam apenas =, !=, IN e NOT IN.")
        if operator in {"=", "IN"}:
            return column == resolved
        if operator in {"!=", "NOT IN"}:
            return column != resolved
        fail("currentUser() aceita apenas =, !=, IN e NOT IN em assignee, creator ou watcher.")
    if field in {"assignee_user_id", "creator_id", "__watcher"} and operator in {"=", "!=", "IN", "NOT IN"}:
        if operator in {"IN", "NOT IN"}:
            if not raw.startswith("(") or not raw.endswith(")"):
                fail("Use IN (usuario1, usuario2) para consultar contas.")
            identities = [_value(item).strip() for item in raw[1:-1].split(",") if item.strip()]
        else:
            identities = [_value(raw).strip()]
        if not identities or len(identities) > 30:
            fail("A lista de contas precisa conter de 1 a 30 valores.")
        matches = []
        for identity in identities:
            if re.fullmatch(r"(?i)currentUser\(\)", identity):
                if actor_user_id is None:
                    fail("currentUser() exige usuário autenticado.")
                matches.append(
                    _watcher_exists(actor_user_id)
                    if field == "__watcher"
                    else column == actor_user_id
                )
            elif identity.isdigit():
                user_id = int(identity)
                matches.append(
                    _watcher_exists(user_id)
                    if field == "__watcher"
                    else column == user_id
                )
            else:
                username = identity
                if field == "__watcher":
                    matches.append(
                        select(TaskWatcher.id)
                        .join(User, User.id == TaskWatcher.user_id)
                        .where(
                            TaskWatcher.task_id == Task.id,
                            User.username == username,
                        )
                        .exists()
                    )
                else:
                    matches.append(
                        select(User.id)
                        .where(User.id == column, User.username == username)
                        .exists()
                    )
        condition = or_(*matches)
        return ~condition if operator in {"!=", "NOT IN"} else condition
    if operator in {"IN", "NOT IN"}:
        if field in {"__release_id", "__component_id", "sprint_id"}:
            values = _list_values(raw)
            clauses = [
                _sprint_exists(item) if field == "sprint_id" else _related_exists(field, item)
                for item in values
            ]
            return or_(*clauses) if operator == "IN" else and_(*(~clause for clause in clauses))
        if not raw.startswith("(") or not raw.endswith(")"):
            fail("Use IN (valor1, valor2) para consultar listas.")
        values = [_value(item) for item in raw[1:-1].split(",") if item.strip()]
        if not values or len(values) > 30:
            fail("A lista IN precisa conter de 1 a 30 valores.")
        normalized = [_typed(field, item) for item in values]
        if field in {"__updated_at", "__resolution_date"}:
            clauses = [_date_or_exact_match(column, item) for item in normalized]
            return or_(*clauses) if operator == "IN" else and_(*(~clause for clause in clauses))
        if field == "__watcher":
            clauses = [_watcher_exists(item) for item in normalized]
            return or_(*clauses) if operator == "IN" else and_(*(~clause for clause in clauses))
        return column.in_(normalized) if operator == "IN" else column.not_in(normalized)
    if field in {"__release_id", "__component_id", "sprint_id"}:
        if operator not in {"=", "!="}:
            fail("Sprint, release/fixVersion e component aceitam apenas =, !=, IN e NOT IN.")
        identity = _value(raw)
        condition = _sprint_exists(identity) if field == "sprint_id" else _related_exists(field, identity)
        return condition if operator == "=" else ~condition
    value = _typed(field, _relative_value(field, raw, current_date=current_date))
    if field == "creator_id" and operator not in {"=", "!=", "IN", "NOT IN"}:
        fail("Creator aceita apenas =, !=, IN e NOT IN.")
    if field == "__watcher":
        if operator not in {"=", "!="}:
            fail("Observador aceita apenas =, !=, IN e NOT IN.")
        condition = _watcher_exists(value)
        return condition if operator == "=" else ~condition
    if field in {"__updated_at", "__resolution_date"} and operator in {"=", "!="}:
        condition = _date_or_exact_match(column, value)
        return condition if operator == "=" else ~condition
    if field == "__resolution_date" and operator in {">", ">=", "<", "<="} and len(value) == 10:
        start = datetime.combine(date.fromisoformat(value), time.min, timezone.utc).isoformat()
        end = datetime.combine(date.fromisoformat(value) + timedelta(days=1), time.min, timezone.utc).isoformat()
        return {
            ">": column >= end,
            ">=": column >= start,
            "<": column < start,
            "<=": column < end,
        }[operator]
    if field == "labels":
        if operator not in {"=", "~"}:
            fail("Etiqueta aceita apenas = ou ~.")
        return cast(Task.labels, String).contains(str(value), autoescape=True)
    if field == "__text":
        if operator != "~":
            fail("O campo text aceita apenas o operador ~.")
        needle = str(value)
        custom_values = select(SchemaVersion.id).where(
            SchemaVersion.task_id == Task.id,
            cast(SchemaVersion.values, String).contains(needle, autoescape=True),
        )
        comments = select(Comment.id).where(
            Comment.task_id == Task.id,
            Comment.body.contains(needle, autoescape=True),
        )
        return or_(
            Task.title.contains(needle, autoescape=True),
            Task.description.contains(needle, autoescape=True),
            custom_values.exists(),
            comments.exists(),
        )
    if field == "__comment":
        return select(Comment.id).where(
            Comment.task_id == Task.id,
            Comment.body.contains(str(value), autoescape=True),
        ).exists()
    if operator == "=":
        return column == value
    if operator == "!=":
        return column != value
    if operator == "~":
        if field not in {"title", "description"}:
            fail("O operador ~ é permitido para title/summary, description, text e label.")
        return column.contains(str(value), autoescape=True)
    if operator in {">", ">=", "<", "<="}:
        if field not in {"priority", "created_at", "__updated_at", "__resolution_date", "due", "planned_start", "estimated_minutes", "used_minutes"}:
            fail("Comparações de faixa são permitidas em priority, created, updated, resolutiondate, planned_start, due/planned_end, estimated_minutes e used_minutes.")
        return {
            ">": column > value,
            ">=": column >= value,
            "<": column < value,
            "<=": column <= value,
        }[operator]
    fail("Operador não permitido na consulta avançada.")


def _history_boundary(raw, *, after):
    value = _value(raw).strip()
    try:
        if len(value) == 10:
            parsed_date = date.fromisoformat(value)
            if after:
                return datetime.combine(parsed_date + timedelta(days=1), time.min, timezone.utc).isoformat(), True
            return datetime.combine(parsed_date, time.min, timezone.utc).isoformat(), False
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        fail("Datas de status CHANGED devem usar AAAA-MM-DD ou ISO 8601.")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(), False


def _updated_by_boundary(raw, *, current_date=None, end=False):
    value = _value(raw).strip()
    relative = re.fullmatch(r"([+-]?)(\d{1,5})([dw])", value, re.IGNORECASE)
    today = current_date or datetime.now(timezone.utc).date()
    if relative:
        sign, amount_raw, unit = relative.groups()
        amount = int(amount_raw) * (-1 if sign == "-" else 1)
        offset = timedelta(days=amount * (7 if unit.casefold() == "w" else 1))
        boundary_date = today + offset
    else:
        try:
            boundary_date = date.fromisoformat(value.replace("/", "-"))
        except ValueError:
            fail("updatedBy() aceita datas AAAA-MM-DD ou deslocamentos em dias/semanas, como -7d.")
    boundary_time = time.max if end else time.min
    return datetime.combine(boundary_date, boundary_time, timezone.utc).isoformat()


def _history_period(raw):
    period = re.fullmatch(
        rf"\(\s*(?P<start>{HISTORY_VALUE_ATOM})\s*,\s*(?P<end>{HISTORY_VALUE_ATOM})\s*\)",
        raw.strip(),
    )
    if not period:
        fail('DURING exige um intervalo no formato DURING ("início", "fim").')

    def parse_boundary(value, *, end=False):
        value = _value(value).strip()
        try:
            if len(value) == 10:
                parsed_date = date.fromisoformat(value)
                parsed = datetime.combine(
                    parsed_date,
                    time.max if end else time.min,
                    timezone.utc,
                )
            else:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                parsed = parsed.astimezone(timezone.utc)
        except ValueError:
            fail("DURING exige datas AAAA-MM-DD ou instantes ISO 8601.")
        return parsed

    start = parse_boundary(period.group("start"))
    end = parse_boundary(period.group("end"), end=True)
    if end < start:
        fail("O fim do intervalo DURING deve ser igual ou posterior ao início.")
    return start.isoformat(), end.isoformat()


def _history_json(field, raw):
    if raw.casefold() in {"null", "empty"}:
        if field not in {"supplier_id", "sprint_id", "parent_id", "assignee_user_id", "due"}:
            fail(f"{field} não aceita um valor histórico vazio.")
        value = None
    else:
        value = _typed(field, raw)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _history_values(field, raw):
    if not raw.startswith("("):
        return [_history_json(field, _value(raw))]
    source = raw[1:-1]
    values, start, quote = [], 0, None
    for index, char in enumerate(source):
        if quote:
            if char == quote and (index == 0 or source[index - 1] != "\\"):
                quote = None
        elif char in {'"', "'"}:
            quote = char
        elif char == ",":
            value = source[start:index].strip()
            if not value:
                fail("WAS IN contém um valor vazio.")
            values.append(value)
            start = index + 1
    if quote:
        fail("Aspas não foram fechadas em WAS IN.")
    final = source[start:].strip()
    if final:
        values.append(final)
    if not values or len(values) > 30:
        fail("WAS IN precisa conter de 1 a 30 valores.")
    return [_history_json(field, _value(value)) for value in values]


def _custom_history_json(raw):
    source = raw.strip()
    if source.casefold() in {"empty", "null"}:
        return "null"
    if len(source) >= 2 and source[0] == source[-1] and source[0] in {'"', "'"}:
        value = _value(source)
    else:
        try:
            value = json.loads(source)
        except json.JSONDecodeError:
            value = source
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _custom_history_values(raw):
    if not raw.startswith("("):
        return [_custom_history_json(raw)]
    source, start, quote, values = raw[1:-1], 0, None, []
    for index, char in enumerate(source):
        if quote:
            if char == quote and (index == 0 or source[index - 1] != "\\"):
                quote = None
        elif char in {'"', "'"}:
            quote = char
        elif char == ",":
            value = source[start:index].strip()
            if not value:
                fail("WAS IN contém um valor vazio.")
            values.append(_custom_history_json(value))
            start = index + 1
    final = source[start:].strip()
    if quote or not final:
        fail("WAS IN precisa conter valores válidos.")
    values.append(_custom_history_json(final))
    if len(values) > 30:
        fail("WAS IN precisa conter de 1 a 30 valores.")
    return values


def _related_exists(field, identity):
    if field == "__release_id":
        release_ids = select(Release.id)
        if str(identity).isdigit():
            release_ids = release_ids.where(Release.id == int(identity))
        else:
            release_ids = release_ids.where(Release.name == identity)
        return select(TaskRelease.id).where(
            TaskRelease.task_id == Task.id,
            TaskRelease.release_id.in_(release_ids),
        ).exists()
    component_ids = select(Component.id)
    if str(identity).isdigit():
        component_ids = component_ids.where(Component.id == int(identity))
    else:
        component_ids = component_ids.where(Component.name == identity)
    return select(TaskComponent.id).where(
        TaskComponent.task_id == Task.id,
        TaskComponent.component_id.in_(component_ids),
    ).exists()


def _sprint_exists(identity):
    sprint_ids = select(Sprint.id)
    sprint_ids = sprint_ids.where(Sprint.id == Task.sprint_id)
    if str(identity).isdigit():
        sprint_ids = sprint_ids.where(Sprint.id == int(identity))
    else:
        sprint_ids = sprint_ids.where(Sprint.name == identity)
    return sprint_ids.exists()


def _date_or_exact_match(column, value):
    if len(value) == 10:
        start = datetime.combine(date.fromisoformat(value), time.min, timezone.utc).isoformat()
        end = datetime.combine(date.fromisoformat(value) + timedelta(days=1), time.min, timezone.utc).isoformat()
        return and_(column >= start, column < end)
    return column == value


def _watcher_exists(user_id):
    return select(TaskWatcher.id).where(
        TaskWatcher.task_id == Task.id,
        TaskWatcher.user_id == user_id,
    ).exists()


def _updated_column():
    latest_change = select(func.max(Audit.created_at)).where(
        Audit.entity == "task",
        Audit.entity_id == Task.id,
    ).scalar_subquery()
    return func.coalesce(latest_change, Task.created_at)


def _resolution_date_column():
    """Return latest audited completion time only while the task is completed."""
    latest_completion = (
        select(func.max(Audit.created_at))
        .join(TaskFieldChange, TaskFieldChange.audit_id == Audit.id)
        .where(
            Audit.entity == "task",
            Audit.entity_id == Task.id,
            TaskFieldChange.field == "status",
            TaskFieldChange.kind == "value",
            TaskFieldChange.after_json == '"done"',
        )
        .scalar_subquery()
    )
    return case((Task.status == "done", latest_completion), else_=None)


def _resolution_column():
    """Expose the recorded Jira-compatible resolution value for a card."""
    return Task.resolution


def apply_query(
    query,
    source,
    *,
    allow_configuration_history=True,
    actor_user_id=None,
    actor_role=None,
    current_date=None,
):
    """Apply a safe boolean expression with optional allowlisted ordering."""
    source = (source or "").strip()
    if not source:
        return query
    if len(source) > 1000:
        fail("Consulta avançada excede 1000 caracteres.")
    if not allow_configuration_history and re.search(r"\bfield_config_[a-zA-Z][a-zA-Z0-9_]{0,75}\s+(?:CHANGED|WAS)\b", source, re.IGNORECASE):
        fail("A pesquisa do histórico de configuração está restrita a administradores.", 403, "FORBIDDEN")
    ordering = []
    order_match = ORDER.search(source)
    if order_match:
        seen = set()
        for item in order_match.group("fields").split(","):
            parts = item.strip().split()
            order_field = FIELDS.get(parts[0].lower())
            direction = (parts[1] if len(parts) > 1 else "ASC").upper()
            if order_field not in {"priority", "created_at", "__updated_at", "__resolution_date", "__resolution", "due", "planned_start", "estimated_minutes", "used_minutes", "title", "status", "__status_category", "__issue_id"}:
                fail("Ordenação não permitida. Use priority, created, updated, resolution, resolutiondate, planned_start, due/dueDate, estimated_minutes, used_minutes, title/summary, status/statusCategory ou key/id.")
            if order_field in seen:
                fail("Não repita um campo na ordenação.")
            seen.add(order_field)
            ordering.append((order_field, direction))
        source = source[: order_match.start()].strip()
    if source:
        query = query.where(
            _expression(
                source,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                current_date=current_date,
            )
        )
    if ordering:
        clauses = []
        includes_identity = False
        for field, direction in ordering:
            column = (
                Task.id
                if field == "__issue_id"
                else _updated_column()
                if field == "__updated_at"
                else _status_category_rank()
                if field == "__status_category"
                else _resolution_date_column()
                if field == "__resolution_date"
                else _resolution_column()
                if field == "__resolution"
                else getattr(Task, field)
            )
            clauses.append(column.desc() if direction == "DESC" else column.asc())
            includes_identity = includes_identity or field == "__issue_id"
        if not includes_identity:
            clauses.append(Task.id.asc())
        query = query.order_by(*clauses)
    return query


_RELATIVE_DATE = re.compile(
    r"(?i)(now|startOfDay|endOfDay|startOfWeek|endOfWeek|startOfMonth|endOfMonth|startOfYear|endOfYear)\(\)"
    r"(?:\s*([+-])\s*(\d{1,4})\s*([dwMy]))?"
)


def _relative_value(field, raw, *, current_date=None):
    """Resolve a small deterministic UTC date-function allowlist for date fields."""
    match = _RELATIVE_DATE.fullmatch(raw.strip())
    if not match:
        return _value(raw)
    if field not in {"due", "planned_start", "created_at", "__updated_at", "__resolution_date", "__worklog_date"}:
        fail("Funções de data só podem ser usadas nos campos due/planned_end, planned_start, created, updated, resolutiondate e worklogDate.")
    function, sign, amount_raw, unit = match.groups()
    now = datetime.now(timezone.utc)
    if current_date is not None:
        now = datetime.combine(current_date, time(12), timezone.utc)
    start_today = datetime.combine(now.date(), time.min, timezone.utc)
    if function.lower() == "now":
        value = now
    elif function.lower() in {"startofday", "endofday"}:
        value = start_today if function.lower() == "startofday" else start_today + timedelta(days=1, microseconds=-1)
    elif function.lower() in {"startofweek", "endofweek"}:
        value = start_today - timedelta(days=now.weekday())
        if function.lower() == "endofweek":
            value += timedelta(days=7, microseconds=-1)
    elif function.lower() in {"startofmonth", "endofmonth"}:
        value = start_today.replace(day=1)
        if function.lower() == "endofmonth":
            value = value.replace(day=28) + timedelta(days=4)
            value = value.replace(day=1) + timedelta(microseconds=-1)
    elif function.lower() in {"startofyear", "endofyear"}:
        value = start_today.replace(month=1, day=1)
        if function.lower() == "endofyear":
            value = value.replace(year=value.year + 1) - timedelta(microseconds=1)
    else:
        fail("Função de data não permitida.")
    if sign and amount_raw and unit:
        amount = int(amount_raw) * (1 if sign == "+" else -1)
        if unit.lower() == "d":
            value += timedelta(days=amount)
        elif unit.lower() == "w":
            value += timedelta(weeks=amount)
        elif unit == "M":
            month_index = value.year * 12 + value.month - 1 + amount
            year, month = divmod(month_index, 12)
            month = month + 1
            day = min(value.day, calendar.monthrange(year, month)[1])
            value = value.replace(year=year, month=month, day=day)
        elif unit == "y":
            value = value.replace(year=value.year + amount)
    if field in {"due", "planned_start"}:
        return value.date().isoformat()
    return value.isoformat()


def _worklog_date_match(raw, operator, *, current_date=None):
    return _activity_date_match(Hours, raw, operator, current_date=current_date)


def _activity_date_match(model, raw, operator, *, current_date=None):
    value = _relative_value("__worklog_date", raw, current_date=current_date)
    try:
        if len(value) == 10:
            target_date = date.fromisoformat(value)
            boundary = datetime.combine(target_date, time.min, timezone.utc)
            next_day = boundary + timedelta(days=1)
            if operator in {"=", "!="}:
                clauses = (model.created_at >= boundary.isoformat(), model.created_at < next_day.isoformat())
                match = select(model.id).where(model.task_id == Task.id, *clauses).exists()
                return match if operator == "=" else ~match
            value = boundary.isoformat()
        else:
            instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if instant.tzinfo is None:
                instant = instant.replace(tzinfo=timezone.utc)
            value = instant.astimezone(timezone.utc).isoformat()
    except ValueError:
        fail("worklogDate precisa usar AAAA-MM-DD, ISO 8601 ou uma função de data permitida.")
    if operator == "!=":
        exact_match = select(model.id).where(
            model.task_id == Task.id,
            model.created_at == value,
        ).exists()
        return ~exact_match
    comparison = {
        "=": model.created_at == value,
        ">": model.created_at > value,
        ">=": model.created_at >= value,
        "<": model.created_at < value,
        "<=": model.created_at <= value,
    }[operator]
    return select(model.id).where(model.task_id == Task.id, comparison).exists()


def _typed(field, value):
    if field == "priority":
        try:
            return int(value)
        except (TypeError, ValueError):
            fail("priority precisa ser número inteiro.")
    if field == "__issue_id":
        return _task_identity(value)
    if field == "__resolution":
        normalized = value.casefold()
        if normalized not in RESOLUTIONS:
            fail('resolution aceita Done, Fixed, Duplicate, Won\'t Do, Cannot Reproduce ou Other.')
        return next(
            label
            for label in ("Done", "Fixed", "Duplicate", "Won't Do", "Cannot Reproduce", "Other")
            if label.casefold() == normalized
        )
    if field in {"supplier_id", "sprint_id", "parent_id", "assignee_user_id", "creator_id", "__watcher", "__release_id", "__component_id", "__issue_id"}:
        try:
            return int(value)
        except (TypeError, ValueError):
            fail(f"{field} precisa ser um identificador inteiro.")
    if field in {"due", "planned_start", "created_at", "__updated_at", "__resolution_date"}:
        try:
            if field in {"created_at", "__updated_at", "__resolution_date"} and ("T" in value or " " in value):
                parsed_datetime = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed_datetime.tzinfo is None:
                    parsed_datetime = parsed_datetime.replace(tzinfo=timezone.utc)
                return parsed_datetime.astimezone(timezone.utc).isoformat()
            return date.fromisoformat(value).isoformat()
        except ValueError:
            fail(f"{field} precisa estar no formato AAAA-MM-DD.")
    if field in {"estimated_minutes", "used_minutes"}:
        try:
            minutes = int(value)
            if minutes < 0:
                raise ValueError
            return minutes
        except (TypeError, ValueError):
            fail(f"{field} precisa ser um número inteiro de minutos igual ou maior que zero.")
    if field == "status" and (not value or len(value) > 80):
        fail("status precisa identificar uma coluna válida.")
    if field == "approval" and value not in APPROVALS:
        fail("Aprovação desconhecida na consulta.")
    if field == "work_type" and value not in WORK_TYPES:
        fail("Tipo de atividade desconhecido na consulta.")
    return value


def _task_identity(value):
    normalized = _value(value).strip()
    if re.fullmatch(r"OS[-_]\d{1,10}", normalized, re.IGNORECASE):
        normalized = re.sub(r"(?i)^OS[-_]", "", normalized)
    try:
        identity = int(normalized)
    except ValueError:
        fail("linkedIssues() precisa receber um identificador como OS-123.")
    if identity <= 0:
        fail("linkedIssues() precisa receber um identificador positivo.")
    return identity
