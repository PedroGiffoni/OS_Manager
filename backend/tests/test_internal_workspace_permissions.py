from types import SimpleNamespace

from app.security import allowed, effective_permissions


def test_internal_accounts_can_use_workspace_planning_features_without_extra_grants():
    user = SimpleNamespace(role="internal", grants=[])

    for permission in (
        "manage_planning",
        "manage_capacity",
        "manage_workflows",
        "manage_automation",
    ):
        assert allowed(user, permission)
        assert permission in effective_permissions(user)


def test_suppliers_cannot_use_workspace_planning_features():
    user = SimpleNamespace(role="supplier", grants=[])

    for permission in (
        "manage_planning",
        "manage_capacity",
        "manage_workflows",
        "manage_automation",
    ):
        assert not allowed(user, permission)
        assert permission not in effective_permissions(user)


def test_financial_and_administration_permissions_remain_separate():
    user = SimpleNamespace(role="internal", grants=[])

    assert not allowed(user, "view_financial")
    assert not allowed(user, "manage_users")
