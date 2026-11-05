"""Operational measurements over authorized records and immutable audit events."""

from collections import defaultdict
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select
from .models import Audit, Hours, Approval, Sprint, SprintTask, User, Supplier
from .services import STATUSES, get_task, fail
from .reporting import records
from .report_filters import filter_context, filter_summary
from .settings import timestamp_date


def instant(value):
    if not value:
        return None
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return (
            result.replace(tzinfo=timezone.utc)
            if result.tzinfo is None
            else result.astimezone(timezone.utc)
        )
    except (ValueError, TypeError):
        return None


def elapsed(start, end):
    if start is None or end is None or end < start:
        return None
    return (end - start) // timedelta(seconds=1)


def percent(value, total):
    return (
        str(
            (Decimal(value) * 100 / Decimal(total)).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
        )
        if total
        else None
    )


def transition(event):
    details = event.details or {}
    if event.action == "status_changed":
        return details.get("origin"), details.get("destination")
    if event.action == "included_in_sprint":
        return details.get("origin", "backlog"), "todo"
    if event.action == "returned_to_backlog":
        return details.get("previous_status"), "backlog"
    return None


def deadline(row, end):
    due = row.get("due")
    if not due:
        return {"state": "no_due", "late_days": None}
    if end is None:
        return {"state": "unknown", "late_days": None}
    days = (
        datetime.fromisoformat(timestamp_date(end.isoformat())).date()
        - datetime.fromisoformat(due).date()
    ).days
    return {
        "state": ("late" if days > 0 else "on_time")
        if row["status"] == "done"
        else ("overdue" if days > 0 else "within_due"),
        "late_days": max(0, days),
    }


def profile(row, events, hours, approvals, reference, actors, closure=None):
    cut = min(reference, instant(closure) or reference)
    created = instant(row["created_at"])
    ordered = sorted(
        [
            event
            for event in events
            if instant(event.created_at) and instant(event.created_at) <= cut
        ],
        key=lambda event: (instant(event.created_at), event.id),
    )
    issues = []
    if not created or created > cut:
        issues.append("Data de criação inválida para o instante observado.")
    complete_start = any(event.action == "created" for event in ordered)
    if not complete_start:
        issues.append(
            "Sem evento auditado de criação; etapas anteriores ao primeiro movimento são desconhecidas."
        )
    phase = "backlog" if complete_start else None
    entered = created if complete_start else None
    entry_actor = next(
        (
            actors.get(event.actor_id, str(event.actor_id))
            for event in ordered
            if event.action == "created"
        ),
        None,
    )
    periods, timeline, cycles, completions = [], [], [], []
    cycle_start, cycle_valid, cycle_kind = None, True, "production"
    history_valid = complete_start and created is not None
    # A closure snapshot represents the state immediately before automatic return.
    closing_return = None
    if row.get("read_only") and row["status"] != "backlog":
        closing_return = next((event.id for event in reversed(ordered) if transition(event)), None)
        if not any(
            event.id == closing_return
            and event.action == "returned_to_backlog"
            and event.details.get("sprint_id") == row.get("sprint_id")
            for event in ordered
        ):
            closing_return = None
    for event in ordered:
        if event.id == closing_return:
            continue
        when = instant(event.created_at)
        actor = actors.get(event.actor_id, str(event.actor_id))
        change = transition(event)
        if change:
            origin, target = change
            if origin not in STATUSES or target not in STATUSES:
                issues.append("Evento de etapa inválido.")
                history_valid = cycle_valid = False
                continue
            valid = phase == origin and entered is not None and when >= entered
            if phase is not None:
                periods.append(
                    {
                        "status": phase,
                        "entered_at": entered.isoformat() if entered else None,
                        "exited_at": when.isoformat(),
                        "duration_seconds": elapsed(entered, when)
                        if valid and phase != "done"
                        else None,
                        "complete": valid,
                        "open": False,
                        "entry_actor": entry_actor,
                        "exit_actor": actor,
                    }
                )
            if not valid:
                issues.append(
                    "Faltam transições entre etapas; os intervalos afetados não foram estimados."
                )
                history_valid = cycle_valid = False
            if target == "production" and cycle_start is None:
                cycle_start, cycle_kind, cycle_valid = when, "production", True
            if origin == "done" and target == "review":
                cycle_start, cycle_kind, cycle_valid = when, "reopening", True
            if target == "done":
                completions.append(when)
                cycles.append(
                    {
                        "kind": cycle_kind,
                        "started_at": cycle_start.isoformat() if cycle_start else None,
                        "completed_at": when.isoformat(),
                        "duration_seconds": elapsed(cycle_start, when) if cycle_valid else None,
                        "complete": cycle_valid and cycle_start is not None,
                    }
                )
                cycle_start = None
            phase, entered, entry_actor = target, when, actor
        timeline.append(
            {
                "id": event.id,
                "action": event.action,
                "at": event.created_at,
                "actor": actor,
                "origin": change[0] if change else None,
                "destination": change[1] if change else None,
                "reason": str((event.details or {}).get("reason") or ""),
                "hours_version": (event.details or {}).get("hours_version"),
                "sprint_id": (event.details or {}).get("sprint_id"),
            }
        )
    consistent = phase == row["status"] and entered is not None
    if not consistent:
        issues.append("A etapa atual não está integralmente comprovada pelo histórico disponível.")
        history_valid = False
    if phase is not None:
        periods.append(
            {
                "status": phase,
                "entered_at": entered.isoformat() if entered else None,
                "exited_at": None,
                "duration_seconds": elapsed(entered, cut)
                if consistent and phase != "done"
                else None,
                "complete": consistent,
                "open": True,
                "entry_actor": entry_actor,
                "exit_actor": None,
            }
        )
    if cycle_start is not None:
        cycles.append(
            {
                "kind": cycle_kind,
                "started_at": cycle_start.isoformat(),
                "completed_at": None,
                "duration_seconds": elapsed(cycle_start, cut)
                if cycle_valid and consistent
                else None,
                "complete": cycle_valid and consistent,
            }
        )
    totals = []
    for state in STATUSES:
        visits = [period for period in periods if period["status"] == state]
        seconds = (
            None
            if state == "done"
            or any(period["duration_seconds"] is None for period in visits)
            or (not history_valid and not visits)
            else sum(period["duration_seconds"] for period in visits)
        )
        totals.append({"status": state, "duration_seconds": seconds, "visits": len(visits)})
    submitted = {
        entry.version: entry
        for entry in hours
        if instant(entry.created_at) and instant(entry.created_at) <= cut
    }
    decided = {
        entry.hours_version: entry
        for entry in approvals
        if instant(entry.created_at) and instant(entry.created_at) <= cut
    }
    approval_rows = []
    for version, entry in sorted(submitted.items()):
        decision = decided.get(version)
        approval_rows.append(
            {
                "hours_version": version,
                "submitted_at": entry.created_at,
                "used_minutes": entry.used_minutes,
                "estimated_minutes": entry.estimated_minutes,
                "submitted_by": actors.get(entry.author_id, str(entry.author_id)),
                "decision_at": decision.created_at if decision else None,
                "decision_by": actors.get(decision.author_id, str(decision.author_id))
                if decision
                else None,
                "state": ("approved" if decision.approved else "rejected")
                if decision
                else "pending",
                "reason": decision.reason if decision else "",
                "waiting_seconds": elapsed(
                    instant(entry.created_at), instant(decision.created_at) if decision else cut
                ),
            }
        )
    current_approval = decided.get(row["hours_version"])
    estimated = row["estimated_minutes"]
    last_change = max((instant(event.created_at) for event in ordered), default=None)
    final_completion = completions[-1] if completions and row["status"] == "done" else None
    missing = []
    if not row.get("supplier_id"):
        missing.append("Fornecedor para registrar as horas")
    for field in row["fields"]:
        if not set(field["required_for"]) & {"todo", "production"}:
            continue
        value = (
            row.get(field["native_key"])
            if field["type"] == "native"
            else row["values"].get(field["id"])
        )
        if (
            value is None
            or value == ""
            or value == []
            or (field["type"] == "checkbox" and value is not True)
            or (field.get("native_key") == "estimated_minutes" and not value)
        ):
            missing.append(field["label"])
    result = {
        "id": row["id"],
        "title": row["title"],
        "status": row["status"],
        "supplier_id": row["supplier_id"],
        "sprint_id": row["sprint_id"],
        "priority": row["priority"],
        "fields": row["fields"],
        "values": row["values"],
        "due": row["due"],
        "created_at": row["created_at"],
        "as_of": cut.isoformat(),
        "historical": bool(row.get("read_only")),
        "history_complete": history_valid and consistent,
        "history_issues": list(dict.fromkeys(issues)),
        "age_seconds": elapsed(created, cut),
        "current_phase_seconds": elapsed(entered, cut) if consistent and phase != "done" else None,
        "current_phase_entered_at": entered.isoformat() if consistent else None,
        "idle_seconds": elapsed(last_change, cut),
        "lead_time_seconds": elapsed(created, completions[0])
        if history_valid and completions
        else None,
        "completed_at": final_completion.isoformat() if final_completion else None,
        "cycles": cycles,
        "phases": totals,
        "periods": periods,
        "timeline": timeline,
        "approval_history": approval_rows,
        "reopen_count": sum(event.action == "reopened" for event in ordered),
        "rejection_count": sum(not entry.approved for entry in decided.values()),
        "resubmission_count": sum(
            1
            for version, entry in submitted.items()
            if any(
                other.hours_version < version
                and not other.approved
                and instant(other.created_at) <= instant(entry.created_at)
                for other in decided.values()
            )
        ),
        "sprints_visited": len(
            {
                event.details.get("sprint_id")
                for event in ordered
                if event.action == "included_in_sprint"
            }
        ),
        "estimated_minutes": estimated if estimated > 0 else None,
        "used_minutes": row["used_minutes"],
        "approved_minutes": current_approval.used_minutes
        if current_approval and current_approval.approved and row["approval"] == "approved"
        else 0,
        "hours_deviation_minutes": row["used_minutes"] - estimated if estimated > 0 else None,
        "hours_deviation_percent": percent(row["used_minutes"] - estimated, estimated)
        if estimated > 0
        else None,
        "approval": row["approval"],
        "current_submission_present": row["hours_version"] in submitted,
        "deadline": deadline(row, final_completion if row["status"] == "done" else cut),
        "production_missing_fields": list(dict.fromkeys(missing)),
    }
    for key in ["cost_cents", "rate_cents"]:
        if key in row:
            result[key] = row[key]
    return result


def build_cards(db, rows, reference):
    ids = [row["id"] for row in rows]
    event_map, hours_map, approval_map = defaultdict(list), defaultdict(list), defaultdict(list)
    for model, target in [(Audit, event_map), (Hours, hours_map), (Approval, approval_map)]:
        if not ids:
            continue
        query = (
            select(model).where(model.entity == "task", model.entity_id.in_(ids))
            if model is Audit
            else select(model).where(model.task_id.in_(ids))
        )
        for entry in db.scalars(query):
            target[entry.entity_id if model is Audit else entry.task_id].append(entry)
    actor_ids = (
        {event.actor_id for values in event_map.values() for event in values}
        | {entry.author_id for values in hours_map.values() for entry in values}
        | {entry.author_id for values in approval_map.values() for entry in values}
    )
    actors = (
        {user.id: user.username for user in db.scalars(select(User).where(User.id.in_(actor_ids)))}
        if actor_ids
        else {}
    )
    suppliers = (
        {
            supplier.id: supplier.name
            for supplier in db.scalars(
                select(Supplier).where(
                    Supplier.id.in_({row["supplier_id"] for row in rows if row["supplier_id"]})
                )
            )
        }
        if rows
        else {}
    )
    result = [
        profile(
            row,
            event_map[row["id"]],
            hours_map[row["id"]],
            approval_map[row["id"]],
            reference,
            actors,
            row.get("history_as_of"),
        )
        for row in rows
    ]
    for card in result:
        card["supplier_name"] = suppliers.get(card["supplier_id"])
    return result


def group_count(rows, key):
    groups = defaultdict(int)
    for row in rows:
        groups[row.get(key)] += 1
    return [
        {"value": key, "count": value}
        for key, value in sorted(groups.items(), key=lambda item: str(item[0]))
    ]


def summary(cards, idle_days):
    backlog = [card for card in cards if card["status"] == "backlog"]
    return {
        "cards": len(cards),
        "complete_histories": sum(card["history_complete"] for card in cards),
        "open": sum(card["status"] != "done" for card in cards),
        "overdue": sum(card["deadline"]["state"] == "overdue" for card in cards),
        "reopened": sum(card["reopen_count"] > 0 for card in cards),
        "waiting_approval": sum(
            card["status"] == "review"
            and card["approval"] in {"pending", "resubmitted"}
            and card["current_submission_present"]
            for card in cards
        ),
        "by_status": group_count(cards, "status"),
        "phase_seconds": [
            {
                "status": state,
                "duration_seconds": sum(
                    value["duration_seconds"]
                    for card in cards
                    for value in card["phases"]
                    if value["status"] == state and value["duration_seconds"] is not None
                ),
                "measured_cards": sum(
                    any(
                        value["status"] == state and value["duration_seconds"] is not None
                        for value in card["phases"]
                    )
                    for card in cards
                ),
            }
            for state in STATUSES
            if state != "done"
        ],
        "backlog": {
            "count": len(backlog),
            "unassigned": sum(not card["supplier_id"] for card in backlog),
            "overdue": sum(card["deadline"]["state"] == "overdue" for card in backlog),
            "idle_days": idle_days,
            "idle": sum(
                card["idle_seconds"] is not None and card["idle_seconds"] >= idle_days * 86400
                for card in backlog
            ),
            "ready": sum(not card["production_missing_fields"] for card in backlog),
            "by_priority": group_count(backlog, "priority"),
            "by_supplier": group_count(backlog, "supplier_id"),
            "oldest": [
                card["id"] for card in sorted(backlog, key=lambda card: card["created_at"])[:10]
            ],
        },
    }


def sprint_summaries(db, user, selected_ids, criteria, reference, context):
    if not selected_ids:
        return []
    ids = set(db.scalars(select(SprintTask.sprint_id).where(SprintTask.task_id.in_(selected_ids))))
    if criteria.get("sprint_id") is not None:
        ids &= {criteria["sprint_id"]}
    result = []
    for sprint in db.scalars(select(Sprint).where(Sprint.id.in_(ids)).order_by(Sprint.id)):
        events = list(
            db.scalars(
                select(Audit)
                .where(Audit.entity == "sprint", Audit.entity_id == sprint.id)
                .order_by(Audit.created_at, Audit.id)
            )
        )
        starts = [event for event in events if event.action == "start"]
        closes = [event for event in events if event.action == "close"]
        started = instant(starts[0].created_at) if starts else None
        cut = (
            min(reference, instant(closes[-1].created_at))
            if sprint.state == "closed" and closes
            else reference
        )
        row_context = context
        rows = [
            row
            for row in records(
                db,
                user,
                criteria.get("status"),
                sprint.id,
                criteria.get("supplier_id"),
                criteria.get("starts"),
                criteria.get("ends"),
                row_context,
            )
            if row["id"] in selected_ids
        ]
        # A custom field may exist only in another sprint's historical schema.
        cards = build_cards(db, rows, cut)
        task_events = (
            list(
                db.scalars(
                    select(Audit).where(
                        Audit.entity == "task", Audit.entity_id.in_([row["id"] for row in rows])
                    )
                )
            )
            if rows
            else []
        )
        membership = [
            event
            for event in task_events
            if event.action == "included_in_sprint"
            and event.details.get("sprint_id") == sprint.id
            and instant(event.created_at) <= cut
        ]
        known_ids = {event.entity_id for event in membership}
        complete = bool(started) and all(row["id"] in known_ids for row in rows)
        initial = (
            {int(identity) for identity in starts[0].details["committed_task_ids"]}
            if starts and "committed_task_ids" in starts[0].details
            else {
                event.entity_id
                for event in membership
                if started and instant(event.created_at) <= started
            }
        )
        initial &= {row["id"] for row in rows}
        done = {row["id"] for row in rows if row["status"] == "done"}
        added = {
            event.entity_id
            for event in membership
            if started and instant(event.created_at) > started
        }
        returned = {
            event.entity_id
            for event in task_events
            if event.action == "returned_to_backlog"
            and event.details.get("sprint_id") == sprint.id
            and instant(event.created_at) <= cut
        }
        effort = {
            "estimated_minutes": sum(row["estimated_minutes"] for row in rows),
            "used_minutes": sum(row["used_minutes"] for row in rows),
            "estimated_cards": sum(row["estimated_minutes"] > 0 for row in rows),
            "approved_minutes": sum(card["approved_minutes"] for card in cards),
        }
        if rows and "cost_cents" in rows[0]:
            effort["cost_cents"] = sum(row["cost_cents"] for row in rows)
        daily = defaultdict(int)
        for card in cards:
            for cycle in card["cycles"]:
                moment = instant(cycle["completed_at"])
                if moment and started and started <= moment <= cut:
                    daily[timestamp_date(moment.isoformat())] += 1
        result.append(
            {
                "id": sprint.id,
                "name": sprint.name,
                "state": sprint.state,
                "as_of": cut.isoformat(),
                "started_at": started.isoformat() if started else None,
                "history_complete": complete,
                "initial_cards": len(initial) if complete else None,
                "initial_done": len(initial & done) if complete else None,
                "commitment_percent": percent(len(initial & done), len(initial))
                if complete
                else None,
                "added_after_start": len(added) if complete else None,
                "done": len(done),
                "pending": len(rows) - len(done),
                "returned": len(returned),
                "scope_cards": len(rows),
                "completion_events_by_day": [
                    {"date": day, "count": count} for day, count in sorted(daily.items())
                ],
                **effort,
            }
        )
    return result


def report(db, user, criteria, *, idle_days=7, reference=None):
    reference = reference or datetime.now(timezone.utc)
    context = filter_context(
        db, user, criteria.get("field_filters", "[]"), criteria.get("sprint_id")
    )
    rows = records(
        db,
        user,
        criteria.get("status"),
        criteria.get("sprint_id"),
        criteria.get("supplier_id"),
        criteria.get("starts"),
        criteria.get("ends"),
        context,
    )
    cards = build_cards(db, rows, reference)
    minimum = criteria.get("min_phase_hours")
    if minimum not in (None, ""):
        from .report_filters import decimal

        minimum = decimal(minimum)
        if minimum < 0:
            fail("O tempo mínimo de fase não pode ser negativo.")
        cards = [
            card
            for card in cards
            if card["current_phase_seconds"] is not None
            and Decimal(card["current_phase_seconds"]) >= minimum * 3600
        ]
    if criteria.get("overdue_only"):
        cards = [card for card in cards if card["deadline"]["state"] in {"overdue", "late"}]
    if criteria.get("only_reopened"):
        cards = [card for card in cards if card["reopen_count"] > 0]
    if criteria.get("approval_state"):
        cards = [card for card in cards if card["approval"] == criteria["approval_state"]]
    totals = summary(cards, idle_days)
    events = [event for card in cards for event in card["timeline"]]
    start_day, end_day = criteria.get("starts"), criteria.get("ends")
    if start_day:
        events = [event for event in events if instant(event["at"]).date() >= start_day]
    if end_day:
        events = [event for event in events if instant(event["at"]).date() <= end_day]
    totals["recorded_flow"] = {
        "created": sum(event["action"] == "created" for event in events),
        "started": sum(event["destination"] == "production" for event in events),
        "completed": sum(event["destination"] == "done" for event in events),
        "returned": sum(event["action"] == "returned_to_backlog" for event in events),
        "basis": "Eventos na janela UTC informada, somente dos cards selecionados pela criação; não é um censo geral de todos os eventos.",
    }
    return {
        "as_of": reference.isoformat(),
        "filters": filter_summary(*context),
        "period_basis": "Período seleciona a criação UTC das atividades. Tempos abrangem o histórico até o instante observado; sprint encerrada usa o encerramento.",
        "total": len(cards),
        "summary": totals,
        "sprints": sprint_summaries(
            db, user, {card["id"] for card in cards}, criteria, reference, context
        ),
        "backlog_oldest": [
            {
                key: card[key]
                for key in [
                    "id",
                    "title",
                    "priority",
                    "supplier_name",
                    "created_at",
                    "age_seconds",
                    "current_phase_seconds",
                    "idle_seconds",
                    "production_missing_fields",
                    "history_complete",
                ]
            }
            for card in sorted(
                (card for card in cards if card["status"] == "backlog"),
                key=lambda card: card["created_at"],
            )[:10]
        ],
        "items": cards,
    }


def card_detail(db, user, identity, sprint_id=None):
    get_task(db, user, identity)
    rows = [row for row in records(db, user, sprint_id=sprint_id) if row["id"] == identity]
    if not rows:
        fail("Atividade não encontrada neste recorte.", 404)
    return build_cards(db, rows, datetime.now(timezone.utc))[0]
