"""Version diffs for business mutations; no endpoints modify or delete audit events."""

from copy import deepcopy


def changes(before, after):
    return [
        {"field": key, "before": deepcopy(before.get(key)), "after": deepcopy(value)}
        for key, value in after.items()
        if before.get(key) != value
    ]


def field_changes(previous, fields, values):
    old_fields = {f["id"]: f for f in previous.fields} if previous else {}
    new_fields = {f["id"]: f for f in fields}
    old_values = previous.values if previous else {}
    result = []
    for key in sorted(old_fields.keys() | new_fields.keys()):
        old, new = old_fields.get(key), new_fields.get(key)
        definition = new or old
        visibility = sorted(set((old or new)["visible_to"]) & set((new or old)["visible_to"]))
        for kind, before, after in [
            ("configuration", old, new),
            ("value", old_values.get(key), values.get(key)),
        ]:
            if before != after:
                result.append(
                    {
                        "field": key,
                        "label": definition["label"],
                        "kind": kind,
                        "before": deepcopy(before),
                        "after": deepcopy(after),
                        "visible_to": visibility,
                    }
                )
    return result


def visible_details(details, user, financial, current_fields):
    def clean(value):
        if isinstance(value, dict):
            return {
                key: clean(item)
                for key, item in value.items()
                if financial or "cost" not in key and "rate" not in key
            }
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    result = clean(details)
    if "changes" in details:
        result["changes"] = [
            clean(change)
            for change in details["changes"]
            if (
                (financial or "cost" not in change["field"] and "rate" not in change["field"])
                and ("visible_to" not in change or user.role in change["visible_to"])
                and (
                    change["field"] not in current_fields
                    or user.role in current_fields[change["field"]]["visible_to"]
                )
            )
        ]
    return result
