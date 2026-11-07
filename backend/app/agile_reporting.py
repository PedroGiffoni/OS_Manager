"""Derived Agile charts built only from sprint membership and immutable audit events."""

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from statistics import median

from sqlalchemy import and_, or_, select

from .models import Audit, Sprint, SprintTask, Task
from .services import fail


def _instant(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _status_at(task, events, boundary):
    status = "backlog"
    created = _instant(task.created_at)
    if created and created > boundary:
        return None
    for event in events:
        happened = _instant(event.created_at)
        if happened and happened <= boundary:
            status = (event.details or {}).get("destination", status)
    if not events and task.status == "done":
        # Old records without transition audits are conservatively treated as unresolved.
        return "backlog"
    return status


def _percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _forecast(remaining_hours, completed_hours_by_sprint):
    history = completed_hours_by_sprint[-6:]
    median_velocity = median(history) if history else None
    lower_velocity = _percentile(history, 0.25)
    upper_velocity = _percentile(history, 0.75)
    ready = remaining_hours == 0 or (
        len(history) >= 3 and lower_velocity is not None and lower_velocity > 0
    )
    if remaining_hours == 0:
        expected = minimum = maximum = 0.0
    elif ready:
        expected = remaining_hours / median_velocity if median_velocity else None
        minimum = remaining_hours / upper_velocity if upper_velocity else None
        maximum = remaining_hours / lower_velocity if lower_velocity else None
    else:
        expected = minimum = maximum = None
    return {
        "status": "no_remaining_work" if remaining_hours == 0 else "ready" if ready else "insufficient_history" if len(history) < 3 else "zero_lower_velocity",
        "history_sprints": len(history),
        "remaining_planned_hours": round(remaining_hours, 2),
        "median_completed_hours_per_sprint": round(median_velocity, 2) if median_velocity is not None else None,
        "p25_completed_hours_per_sprint": round(lower_velocity, 2) if lower_velocity is not None else None,
        "p75_completed_hours_per_sprint": round(upper_velocity, 2) if upper_velocity is not None else None,
        "expected_sprints": round(expected, 2) if expected is not None else None,
        "minimum_sprints": round(minimum, 2) if minimum is not None else None,
        "maximum_sprints": round(maximum, 2) if maximum is not None else None,
        "method": "Mediana e percentis 25/75 das horas originalmente estimadas concluídas por sprint nas até seis sprints encerradas anteriores.",
    }


def sprint_agile_report(
    db,
    identity,
    jql="",
    *,
    cycle_start_status="production",
    cycle_end_status="done",
    allow_configuration_history=True,
    actor_user_id=None,
    actor_role=None,
):
    if cycle_start_status == cycle_end_status:
        fail("As etapas inicial e final do ciclo devem ser diferentes.")
    sprint = db.get(Sprint, identity)
    if not sprint or sprint.archived:
        fail("Sprint não encontrada.", 404)
    links = list(db.scalars(select(SprintTask).where(SprintTask.sprint_id == identity)))
    task_ids = [link.task_id for link in links]
    if jql.strip():
        from .query_language import apply_query

        matched_ids = set(
            db.scalars(
                apply_query(
                    select(Task.id),
                    jql,
                    allow_configuration_history=allow_configuration_history,
                    actor_user_id=actor_user_id,
                    actor_role=actor_role,
                )
            )
        )
        links = [row for row in links if row.task_id in matched_ids]
        task_ids = [row.task_id for row in links]
    tasks = (
        {row.id: row for row in db.scalars(select(Task).where(Task.id.in_(task_ids)))}
        if task_ids
        else {}
    )
    audits = defaultdict(list)
    if task_ids:
        for event in db.scalars(
            select(Audit)
            .where(
                Audit.entity == "task",
                Audit.entity_id.in_(task_ids),
                Audit.action.in_(["status_changed", "included_in_sprint", "hours_submitted"]),
            )
            .order_by(Audit.created_at, Audit.id)
        ):
            audits[event.entity_id].append(event)
    sprint_starts = list(
        db.scalars(
            select(Audit)
            .where(Audit.entity == "sprint", Audit.entity_id == identity, Audit.action == "start")
            .order_by(Audit.id.desc())
        )
    )
    sprint_start = sprint_starts[0] if sprint_starts else None
    start_details = (sprint_start.details or {}) if sprint_start else {}
    committed_at_start = set(start_details.get("committed_task_ids", []))
    committed_estimates = start_details.get("committed_estimates", {})
    sprint_started_at = _instant(sprint_start.created_at) if sprint_start else None

    start = date.fromisoformat(sprint.starts)
    end = date.fromisoformat(sprint.ends)
    today = datetime.now(timezone.utc).date()
    chart_end = min(end, today)
    days = max(0, (chart_end - start).days) + 1
    if days > 366:
        fail("O relatório ágil limita a série diária a 366 dias.")

    burndown, burnup, effort_burndown, cumulative, cycle_times = [], [], [], [], []
    for identity_task, task in tasks.items():
        events = audits[identity_task]
        cycle_started_at = None
        for event in events:
            destination = (event.details or {}).get("destination")
            happened = _instant(event.created_at)
            if not happened:
                continue
            if destination == cycle_start_status and cycle_started_at is None:
                cycle_started_at = happened
            if destination == cycle_end_status and cycle_started_at:
                cycle_times.append(
                    {
                        "task_id": task.id,
                        "started_on": cycle_started_at.date().isoformat(),
                        "completed_on": happened.date().isoformat(),
                        "days": round(
                            max(0, (happened - cycle_started_at).total_seconds() / 86400), 2
                        ),
                    }
                )
                cycle_started_at = None

    cycle_times.sort(key=lambda item: (item["completed_on"], item["task_id"]))
    cycle_days = [item["days"] for item in cycle_times]
    control_chart = {
        "sample_count": len(cycle_days),
        "average_days": round(sum(cycle_days) / len(cycle_days), 2) if cycle_days else None,
        "p50_days": round(_percentile(cycle_days, 0.50), 2) if cycle_days else None,
        "p85_days": round(_percentile(cycle_days, 0.85), 2) if cycle_days else None,
        "p95_days": round(_percentile(cycle_days, 0.95), 2) if cycle_days else None,
        "minimum_days": min(cycle_days) if cycle_days else None,
        "maximum_days": max(cycle_days) if cycle_days else None,
    }
    for index, item in enumerate(cycle_times):
        item["cycle_number"] = index + 1

    total_estimated = sum(
        (row.snapshot or {}).get(
            "estimated_minutes",
            tasks[row.task_id].estimated_minutes if row.task_id in tasks else 0,
        )
        for row in links
    )
    for day_offset in range(days):
        current_day = start + timedelta(days=day_offset)
        boundary = datetime.combine(current_day, datetime.max.time(), tzinfo=timezone.utc)
        counts = Counter()
        unresolved = 0
        for task_id, task in tasks.items():
            state = _status_at(task, audits[task_id], boundary)
            if state is None:
                continue
            counts[state] += 1
            if state != "done":
                unresolved += 1
        burndown.append({"date": current_day.isoformat(), "remaining": unresolved})
        burnup.append({"date": current_day.isoformat(), "completed": counts.get("done", 0)})
        cumulative.append({"date": current_day.isoformat(), **dict(counts)})

        scope_minutes = 0
        remaining_minutes = 0
        for task_id, task in tasks.items():
            task_events = audits[task_id]
            inclusion = next(
                (
                    event
                    for event in task_events
                    if getattr(event, "action", None) == "included_in_sprint"
                    and (event.details or {}).get("sprint_id") == identity
                ),
                None,
            )
            if task_id in committed_at_start and sprint_started_at:
                active_since = sprint_started_at
                estimate = committed_estimates.get(str(task_id))
                if estimate is None:
                    estimate = getattr(task, "estimated_minutes", 0)
            elif inclusion:
                active_since = _instant(inclusion.created_at)
                estimate = (inclusion.details or {}).get(
                    "estimated_minutes", getattr(task, "estimated_minutes", 0)
                )
            else:
                continue
            if active_since is None or active_since > boundary:
                continue

            estimate_events = []
            for event in task_events:
                happened = _instant(event.created_at)
                if not happened or happened <= active_since or happened > boundary:
                    continue
                for change in (event.details or {}).get("changes", []):
                    if change.get("field") == "estimated_minutes" and "after" in change:
                        estimate_events.append((happened, getattr(event, "id", 0), change["after"]))
            for _, _, estimate_after in sorted(estimate_events):
                if isinstance(estimate_after, int) and estimate_after >= 0:
                    estimate = estimate_after

            scope_minutes += estimate or 0
            if _status_at(task, task_events, boundary) != "done":
                remaining_minutes += estimate or 0
        effort_burndown.append(
            {
                "date": current_day.isoformat(),
                "remaining_hours": round(remaining_minutes / 60, 2),
                "scope_hours": round(scope_minutes / 60, 2),
            }
        )

    completed = sum(
        1
        for row in links
        if (row.final_status or (tasks.get(row.task_id).status if tasks.get(row.task_id) else ""))
        == "done"
    )
    completed_minutes = sum(
        (row.snapshot or {}).get(
            "estimated_minutes", tasks[row.task_id].estimated_minutes if row.task_id in tasks else 0
        )
        for row in links
        if (row.final_status or (tasks.get(row.task_id).status if tasks.get(row.task_id) else ""))
        == "done"
    )
    sprint_issues = {"completed": [], "not_completed": [], "added_during_sprint": []}
    for link in links:
        task = tasks.get(link.task_id)
        snapshot = link.snapshot or {}
        final_status = link.final_status or (task.status if task else "")
        estimate = snapshot.get(
            "estimated_minutes", task.estimated_minutes if task else 0
        )
        issue = {
            "task_id": link.task_id,
            "title": snapshot.get("title") or (getattr(task, "title", None) if task else None) or f"OS-{link.task_id}",
            "status": final_status,
            "estimated_hours": round((estimate or 0) / 60, 2),
        }
        sprint_issues["completed" if final_status == "done" else "not_completed"].append(issue)
        if sprint_started_at and link.task_id not in committed_at_start and any(
            event.action == "included_in_sprint"
            and (event.details or {}).get("sprint_id") == identity
            and (happened := _instant(event.created_at)) is not None
            and happened > sprint_started_at
            for event in audits[link.task_id]
        ):
            sprint_issues["added_during_sprint"].append(issue)
    for issues in sprint_issues.values():
        issues.sort(key=lambda item: (item["task_id"]))
    velocity = []
    closed_sprints = list(
        db.scalars(
            select(Sprint)
            .where(Sprint.state == "closed", Sprint.archived.is_(False))
            .order_by(Sprint.starts.desc(), Sprint.id.desc())
            .limit(100)
        )
    )
    matched_history_ids = None
    if jql.strip():
        from .query_language import apply_query

        matched_history_ids = set(
            db.scalars(
                apply_query(
                    select(Task.id),
                    jql,
                    allow_configuration_history=allow_configuration_history,
                    actor_user_id=actor_user_id,
                    actor_role=actor_role,
                )
            )
        )
    for closed in reversed(closed_sprints[:6]):
        closed_links = list(db.scalars(select(SprintTask).where(SprintTask.sprint_id == closed.id)))
        if matched_history_ids is not None:
            closed_links = [row for row in closed_links if row.task_id in matched_history_ids]
        done_links = [row for row in closed_links if row.final_status == "done"]
        planned_minutes = sum(
            (row.snapshot or {}).get("estimated_minutes", 0) for row in closed_links
        )
        done_minutes = sum((row.snapshot or {}).get("estimated_minutes", 0) for row in done_links)
        velocity.append(
            {
                "sprint": closed.name,
                "planned_hours": round(planned_minutes / 60, 2),
                "completed_hours": round(done_minutes / 60, 2),
            }
        )

    previous_sprints = list(
        db.scalars(
            select(Sprint)
            .where(
                Sprint.state == "closed",
                Sprint.archived.is_(False),
                or_(
                    Sprint.starts < sprint.starts,
                    and_(Sprint.starts == sprint.starts, Sprint.id < sprint.id),
                ),
            )
            .order_by(Sprint.starts.desc(), Sprint.id.desc())
            .limit(6)
        )
    )
    previous_sprints.reverse()
    historical_completed_minutes = []
    for closed in previous_sprints:
        closed_links = list(db.scalars(select(SprintTask).where(SprintTask.sprint_id == closed.id)))
        if matched_history_ids is not None:
            closed_links = [row for row in closed_links if row.task_id in matched_history_ids]
        historical_completed_minutes.append(
            sum(
                (row.snapshot or {}).get("estimated_minutes", 0)
                for row in closed_links
                if row.final_status == "done"
            )
            / 60
        )

    remaining_hours = max(0, total_estimated - completed_minutes) / 60
    forecast = _forecast(remaining_hours, historical_completed_minutes)

    return {
        "sprint": {
            "id": sprint.id,
            "name": sprint.name,
            "starts": sprint.starts,
            "ends": sprint.ends,
            "state": sprint.state,
        },
        "filter": {"jql": jql.strip()},
        "summary": {
            "committed_cards": len(links),
            "completed_cards": completed,
            "completion_percent": round(completed * 100 / len(links), 1) if links else 0,
            "planned_hours": round(total_estimated / 60, 2),
            "completed_planned_hours": round(completed_minutes / 60, 2),
        },
        "issues": sprint_issues,
        "burndown": burndown,
        "effort_burndown": effort_burndown,
        "burnup": burnup,
        "cumulative_flow": cumulative,
        "cycle_times": cycle_times,
        "control_chart": control_chart,
        "cycle_window": {
            "start_status": cycle_start_status,
            "end_status": cycle_end_status,
        },
        "velocity": velocity,
        "forecast": forecast,
        "definitions": {
            "burndown": "Cards do sprint ainda não concluídos por dia, reconstituídos pelo histórico imutável de transições.",
            "effort_burndown": "Horas estimadas restantes e escopo estimado total por dia. A composição e a estimativa inicial vêm do evento de início/inclusão, e revisões posteriores vêm do histórico de envio de horas. Sprints iniciadas antes da captura de estimativas usam a estimativa atual como aproximação inicial.",
            "burnup": "Cards concluídos acumulados por dia, conforme transições de status registradas.",
            "velocity": "Horas originalmente estimadas dos cards associados a cada sprint encerrada; não representa horas trabalhadas nem story points.",
            "cycle_time": "Dias corridos entre a entrada na etapa inicial configurada e a etapa final escolhida, por card e ciclo concluído.",
            "control_chart": "Pontos ordenados pela data de conclusão entre as etapas configuradas. P50, P85 e P95 mostram limites percentuais dos ciclos com interpolação linear; não são metas nem SLA.",
            "cumulative_flow": "Contagem diária por status reconstituída das transições registradas.",
            "sprint_issues": "Cards comprometidos na sprint, separados pelo status final; sprints encerradas usam título, status e estimativa do snapshot de encerramento. Adicionados durante a sprint são identificados pela comparação entre o snapshot do evento de início e as inclusões posteriores auditadas.",
        },
    }
