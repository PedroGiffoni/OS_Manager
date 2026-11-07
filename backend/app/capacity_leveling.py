"""Non-mutating capacity leveling recommendations."""

from datetime import date


def recommend_capacity_moves(capacity_by_day, demand_by_day, task_allocations):
    """Move forecast effort between days inside each card window without editing cards."""
    leveled = dict(demand_by_day)
    allocations = [
        {
            **row,
            "days": set(row["days"]),
            "daily": dict(row["daily"]),
        }
        for row in task_allocations
    ]
    recommendations = []

    for source_day in sorted(leveled):
        overloaded = max(0, leveled[source_day] - capacity_by_day[source_day])
        if not overloaded:
            continue
        movable = sorted(
            allocations,
            key=lambda row: (row.get("due") or "", row["task_id"]),
            reverse=True,
        )
        for allocation in movable:
            if not overloaded:
                break
            source_minutes = allocation["daily"].get(source_day, 0)
            if source_minutes <= 0:
                continue
            targets = sorted(
                (
                    day
                    for day in allocation["days"]
                    if day != source_day
                    and capacity_by_day.get(day, 0) > leveled.get(day, 0)
                ),
                key=lambda day: (
                    abs((date.fromisoformat(day) - date.fromisoformat(source_day)).days),
                    day,
                ),
            )
            for target_day in targets:
                if not overloaded:
                    break
                spare = capacity_by_day[target_day] - leveled[target_day]
                moved = min(overloaded, source_minutes, spare)
                if moved <= 0:
                    continue
                allocation["daily"][source_day] -= moved
                allocation["daily"][target_day] = allocation["daily"].get(target_day, 0) + moved
                leveled[source_day] -= moved
                leveled[target_day] += moved
                source_minutes -= moved
                overloaded -= moved
                recommendations.append(
                    {
                        "task_id": allocation["task_id"],
                        "title": allocation["title"],
                        "from_date": source_day,
                        "to_date": target_day,
                        "minutes": moved,
                    }
                )
                if not source_minutes:
                    break

    return leveled, recommendations


def apply_capacity_moves(task_allocations, shifts):
    """Apply validated day/minute moves to an allocation snapshot in memory."""
    by_task = {row["task_id"]: row for row in task_allocations}
    for shift in shifts:
        row = by_task.get(shift.get("task_id"))
        source = shift.get("from_date")
        target = shift.get("to_date")
        minutes = shift.get("minutes")
        if (
            row is None
            or source not in row["days"]
            or target not in row["days"]
            or not isinstance(minutes, int)
            or minutes <= 0
            or row["daily"].get(source, 0) < minutes
        ):
            raise ValueError("O plano de redistribuição não corresponde à previsão atual.")
        row["daily"][source] -= minutes
        row["daily"][target] = row["daily"].get(target, 0) + minutes
    return task_allocations
