"""Allowlisted parsing and signature checks for optional source-control webhooks."""

import hashlib
import hmac
import re
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlsplit


TASK_KEY = re.compile(r"\bOS[-_](\d+)\b", re.IGNORECASE)
_ADAPTERS = {}


@dataclass(frozen=True)
class WebhookAdapter:
    """Trusted-code extension point for normalizing a source-control provider."""

    provider: str
    secret_env: str
    verify: Callable[[str, bytes, object], bool]
    identify: Callable[[object], tuple[str, str]]
    summarize: Callable[[str, dict], tuple[str, str, str, str | None]]


def register_webhook_adapter(adapter: WebhookAdapter):
    if not re.fullmatch(r"[a-z][a-z0-9_-]{1,30}", adapter.provider):
        raise ValueError("Identificador de integração inválido.")
    if adapter.provider in _ADAPTERS:
        raise ValueError(f"Integração já registrada: {adapter.provider}")
    _ADAPTERS[adapter.provider] = adapter


def get_webhook_adapter(provider):
    return _ADAPTERS.get(provider)


def valid_signature(provider: str, secret: str, body: bytes, signature: str) -> bool:
    if not secret:
        return False
    if provider == "github":
        expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    if provider == "bitbucket":
        expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not signature.startswith("sha256="):
            signature = "sha256=" + signature
        return hmac.compare_digest(expected, signature)
    return False


def task_ids(value):
    serialized = str(value)
    return {int(match) for match in TASK_KEY.findall(serialized)}


def safe_url(value):
    if not isinstance(value, str) or len(value) > 1000:
        return ""
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        return ""
    return value


def _mapping(value):
    return value if isinstance(value, dict) else {}


def summarize(provider, event_type, payload):
    payload = _mapping(payload)
    actor, url, occurred = "", "", None
    if provider == "github":
        actor = str(
            _mapping(payload.get("sender")).get("login")
            or _mapping(payload.get("pusher")).get("name")
            or ""
        )[:160]
        occurred = _mapping(payload.get("deployment_status")).get("created_at") or _mapping(
            payload.get("pull_request")
        ).get("updated_at")
        if event_type == "pull_request":
            item = _mapping(payload.get("pull_request"))
            summary = (
                f"Pull request {payload.get('action', 'updated')}: {item.get('title', '')}".strip()
            )
            url = item.get("html_url", "")
        elif event_type == "push":
            commits = payload.get("commits") or []
            summary = (
                f"Push em {str(payload.get('ref', 'branch'))[-120:]} · {len(commits)} commit(s)"
            )
            url = payload.get("compare", "")
        elif event_type == "deployment_status":
            status = _mapping(payload.get("deployment_status"))
            summary = f"Implantação {status.get('state', 'atualizada')} · {status.get('environment', 'ambiente')}"
            url = status.get("target_url") or status.get("environment_url") or ""
        else:
            summary = f"Evento GitHub: {event_type}"
    elif provider == "gitlab":
        actor = str(payload.get("user_username") or payload.get("user_name") or "")[:160]
        item = _mapping(payload.get("object_attributes"))
        occurred = item.get("updated_at") or payload.get("event_created_at")
        url = item.get("url", "")
        label = item.get("title") or payload.get("ref") or ""
        summary = f"{event_type}: {label}".strip()
    else:
        actor = str(_mapping(payload.get("actor")).get("display_name") or "")[:160]
        item = _mapping(payload.get("pullrequest") or payload.get("push"))
        url = _mapping(_mapping(item.get("links")).get("html")).get("href", "")
        title = item.get("title") or _mapping(payload.get("repository")).get("full_name") or ""
        summary = f"{event_type}: {title}".strip()
    summary = " ".join(str(summary).split())[:500]
    return summary, safe_url(url), actor, str(occurred)[:80] if occurred else None


def development_metadata(provider, event_type, payload):
    """Extract a small, provider-neutral development summary without storing raw payloads."""
    if not isinstance(payload, dict):
        return {}
    repository = {}
    branch = ""
    commit = ""
    pull_request = ""
    state = ""
    environment = ""

    if provider == "github":
        repository = _mapping(payload.get("repository"))
        branch = payload.get("ref") or ""
        branch = branch if isinstance(branch, str) else ""
        item = _mapping(payload.get("pull_request"))
        head = _mapping(item.get("head"))
        commit = payload.get("after") or _mapping(payload.get("head_commit")).get("id") or head.get("sha") or ""
        branch = branch or head.get("ref") or ""
        branch = branch if isinstance(branch, str) else ""
        pull_request = item.get("number") or ""
        status = _mapping(payload.get("deployment_status"))
        run = _mapping(payload.get("workflow_run") or payload.get("check_run"))
        state = status.get("state") or run.get("conclusion") or run.get("status") or item.get("state") or ""
        environment = status.get("environment") or run.get("name") or ""
    elif provider == "gitlab":
        repository = _mapping(payload.get("project"))
        branch = payload.get("ref") or ""
        branch = branch if isinstance(branch, str) else ""
        item = _mapping(payload.get("object_attributes"))
        commit = payload.get("checkout_sha") or _mapping(item.get("last_commit")).get("id") or ""
        branch = branch or item.get("source_branch") or ""
        branch = branch if isinstance(branch, str) else ""
        pull_request = item.get("iid") or ""
        state = item.get("state") or payload.get("build_status") or ""
        environment = _mapping(payload.get("environment")).get("name") or payload.get("build_name") or ""
    elif provider == "bitbucket":
        repository = _mapping(payload.get("repository"))
        push = _mapping(payload.get("push"))
        changes = push.get("changes") or []
        change = changes[0] if changes and isinstance(changes[0], dict) else {}
        new_ref = _mapping(change.get("new"))
        target = _mapping(new_ref.get("target"))
        branch = new_ref.get("name") or ""
        branch = branch if isinstance(branch, str) else ""
        commit = target.get("hash") or ""
        item = _mapping(payload.get("pullrequest"))
        pull_request = item.get("id") or ""
        source = _mapping(item.get("source"))
        source_branch = _mapping(source.get("branch"))
        branch = branch or source_branch.get("name") or ""
        branch = branch if isinstance(branch, str) else ""
        commit = commit or _mapping(source.get("commit")).get("hash") or ""
        state = item.get("state") or _mapping(payload.get("commit_status")).get("state") or ""

    repo_name = repository.get("full_name") or repository.get("path_with_namespace") or repository.get("name") or ""
    if branch.startswith("refs/heads/"):
        branch = branch[len("refs/heads/"):]
    metadata = {
        "repository": repo_name,
        "branch": branch,
        "commit": commit,
        "pull_request": pull_request,
        "state": state,
        "environment": environment,
    }
    limits = {"repository": 200, "branch": 240, "commit": 100, "pull_request": 40, "state": 80, "environment": 120}
    return {
        key: str(value).strip()[:limits[key]]
        for key, value in metadata.items()
        if value is not None and str(value).strip()
    }


def _github_verify(secret, body, headers):
    return valid_signature("github", secret, body, headers.get("X-Hub-Signature-256", ""))


def _bitbucket_verify(secret, body, headers):
    return valid_signature("bitbucket", secret, body, headers.get("X-Hub-Signature", ""))


def _gitlab_verify(secret, _body, headers):
    supplied = headers.get("X-Gitlab-Token", "")
    return bool(secret) and hmac.compare_digest(secret, supplied)


def _identify(event_header, delivery_header):
    return lambda headers: (headers.get(event_header, ""), headers.get(delivery_header, ""))


for _adapter in (
    WebhookAdapter(
        "github",
        "GITHUB_WEBHOOK_SECRET",
        _github_verify,
        _identify("X-GitHub-Event", "X-GitHub-Delivery"),
        lambda event_type, payload: summarize("github", event_type, payload),
    ),
    WebhookAdapter(
        "gitlab",
        "GITLAB_WEBHOOK_TOKEN",
        _gitlab_verify,
        _identify("X-Gitlab-Event", "X-Gitlab-Event-UUID"),
        lambda event_type, payload: summarize("gitlab", event_type, payload),
    ),
    WebhookAdapter(
        "bitbucket",
        "BITBUCKET_WEBHOOK_SECRET",
        _bitbucket_verify,
        lambda headers: (
            headers.get("X-Event-Key", ""),
            headers.get("X-Request-UUID", "") or headers.get("X-Hook-UUID", ""),
        ),
        lambda event_type, payload: summarize("bitbucket", event_type, payload),
    ),
):
    register_webhook_adapter(_adapter)
