import hashlib
import hmac
import pytest

from app.integrations import (
    WebhookAdapter,
    development_metadata,
    get_webhook_adapter,
    register_webhook_adapter,
    safe_url,
    summarize,
    task_ids,
    valid_signature,
)


def test_task_key_extraction_and_safe_links():
    assert task_ids({"title": "PR for OS-17", "branch": "feature/OS_22-fix"}) == {17, 22}
    assert safe_url("https://git.example.com/team/pull/1") == "https://git.example.com/team/pull/1"
    assert safe_url("javascript:alert(1)") == ""
    assert safe_url("https://user:secret@example.com/path") == ""


def test_provider_signatures_are_verified_without_leaking_secret():
    body = b'{"action":"opened"}'
    signature = "sha256=" + hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
    assert valid_signature("github", "test-secret", body, signature)
    assert valid_signature("bitbucket", "test-secret", body, signature)
    assert not valid_signature("github", "", body, signature)
    assert not valid_signature("github", "test-secret", body, "sha256=invalid")


def test_webhook_summary_is_bounded_and_uses_https_urls():
    summary, url, actor, occurred = summarize(
        "github",
        "pull_request",
        {
            "action": "opened",
            "sender": {"login": "dev-user"},
            "pull_request": {
                "title": "Feature OS-31",
                "html_url": "https://github.com/org/repo/pull/31",
                "updated_at": "2026-11-06T12:00:00Z",
            },
        },
    )
    assert summary == "Pull request opened: Feature OS-31"
    assert url.endswith("/pull/31")
    assert actor == "dev-user"
    assert occurred == "2026-11-06T12:00:00Z"


def test_provider_metadata_normalizes_pull_request_commit_and_deployment_details():
    github = development_metadata(
        "github",
        "pull_request",
        {
            "repository": {"full_name": "org/repo"},
            "pull_request": {"number": 31, "state": "open", "head": {"ref": "feature/card", "sha": "deadbeef"}},
            "sender": {"login": "contributor"},
            "action": "opened",
        },
    )
    gitlab = development_metadata(
        "gitlab",
        "push",
        {
            "project": {"path_with_namespace": "org/service"},
            "ref": "refs/heads/feature/OS-31",
            "checkout_sha": "abc123",
        },
    )
    assert github == {"repository": "org/repo", "branch": "feature/card", "commit": "deadbeef", "pull_request": "31", "state": "open"}
    assert gitlab == {"repository": "org/service", "branch": "feature/OS-31", "commit": "abc123"}
    assert "sender" not in github


def test_trusted_provider_adapter_is_an_explicit_extension_point():
    adapter = WebhookAdapter(
        provider="test-issue-tracker",
        secret_env="TEST_TRACKER_SECRET",
        verify=lambda secret, body, headers: bool(secret and body and headers.get("X-Test")),
        identify=lambda headers: (headers.get("X-Event", ""), headers.get("X-Delivery", "")),
        summarize=lambda event, payload: (f"{event}: {payload['title']}", "", "", None),
    )
    register_webhook_adapter(adapter)
    registered = get_webhook_adapter("test-issue-tracker")
    assert registered is adapter
    assert registered.verify("local-secret", b"{}", {"X-Test": "ok"})
    assert registered.identify({"X-Event": "updated", "X-Delivery": "d-1"}) == (
        "updated",
        "d-1",
    )
    with pytest.raises(ValueError):
        register_webhook_adapter(adapter)
