"""Arga Labs twin executor.

Allowed tool calls are executed against a stateful Arga Labs *twin* of a real
service (default: the GitHub twin). The twin speaks the upstream API shape, so
this is the closest thing to production execution that is still safe:

- deny  -> zero requests reach the twin; no provision is created
- allow -> exactly one upstream-shaped request hits the twin, and the twin's
           own state (collaborators, hooks) is captured before and after as
           independent evidence

Configuration (environment):
    ARGA_API_KEY        server-to-server key, starts with ``arga_sk_``
    ARGA_TWIN           twin name (default ``github``)
    ARGA_RUN_ID         reuse an existing provision instead of creating one
    ARGA_TTL_MINUTES    lifetime for a provision created by AgentJail (default 10; free plan max)
    ARGA_GITHUB_REPO    ``owner/repo`` the demo tools act on (default ``agentjail/infra``)
    ARGA_GITHUB_TOKEN   twin credential override when env_vars is empty (non-Team plans)

The API key and the twin token stay inside this process. They are never placed
in ledger entries or public results.
"""

from __future__ import annotations

import atexit
import copy
import os
import time
from typing import Any

import httpx

from .executor import ToolExecutionError

ARGA_API_BASE = "https://api.argalabs.com"
PROVISION_PATH = "/validate/twins/provision"
STATUS_PATH = "/validate/twins/provision/{run_id}/status"
TEARDOWN_PATH = "/validate/twins/provision/{run_id}/teardown"

# Only these AgentJail tools may reach the twin. Everything else fails closed.
_ALLOWED_TOOLS = {"create_service_identity", "restart_service", "post_webhook"}
_SECRET_KEYS = {"token", "secret", "password", "api_key", "access_token", "authorization"}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: ("[redacted]" if k.lower() in _SECRET_KEYS or k.lower().endswith("_token") else _redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


class ArgaTwinExecutor:
    """Execute allowed calls against an Arga Labs service twin."""

    provider = "arga_twin"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        twin: str | None = None,
        run_id: str | None = None,
        repo: str | None = None,
        ttl_minutes: int | None = None,
        client: httpx.Client | None = None,
        twin_client_factory: Any | None = None,
    ) -> None:
        self._api_key = api_key or os.getenv("ARGA_API_KEY", "")
        if not self._api_key:
            raise RuntimeError("Arga executor requires ARGA_API_KEY (starts with arga_sk_).")
        self._twin = (twin or os.getenv("ARGA_TWIN", "github")).strip().lower()
        if self._twin != "github":
            raise RuntimeError("Only the 'github' twin is mapped for AgentJail demo tools.")
        self._run_id = run_id or os.getenv("ARGA_RUN_ID") or None
        self._owns_run = self._run_id is None
        self._repo = repo or os.getenv("ARGA_GITHUB_REPO", "agentjail/infra")
        self._ttl = int(ttl_minutes or os.getenv("ARGA_TTL_MINUTES", "10"))
        self._api = client or httpx.Client(
            base_url=ARGA_API_BASE,
            headers={"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"},
            timeout=30.0,
        )
        self._twin_client_factory = twin_client_factory or (
            lambda base_url, token: httpx.Client(
                base_url=base_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "agentjail-executor",
                },
                timeout=30.0,
            )
        )
        self._twin_api: httpx.Client | None = None
        self._base_url: str | None = None
        self._ledger: list[dict[str, Any]] = []
        atexit.register(self.close)

    # ---------------------------------------------------------------- lifecycle
    def _ensure_twin(self) -> httpx.Client:
        if self._twin_api is not None:
            return self._twin_api
        if self._run_id is None:
            r = self._api.post(PROVISION_PATH, json={"twins": [self._twin], "ttl_minutes": self._ttl})
            r.raise_for_status()
            self._run_id = str(r.json()["run_id"])
        deadline = time.monotonic() + 180
        while True:
            s = self._api.get(STATUS_PATH.format(run_id=self._run_id))
            s.raise_for_status()
            status = s.json()
            if status.get("status") == "ready":
                break
            if status.get("status") in {"expired", "cancelled", "failed"} or time.monotonic() > deadline:
                raise RuntimeError(f"Arga twin provision not ready: {status.get('status')}")
            time.sleep(2)
        twin = status["twins"][self._twin]
        self._base_url = str(twin["base_url"]).rstrip("/")
        # Team plans return the twin credential in env_vars. On plans that do
        # not, copy the token from the twin's page in the Arga web app and set
        # ARGA_GITHUB_TOKEN. Without a token the twin answers 401 and every
        # allowed call fails closed.
        token = str(
            (twin.get("env_vars") or {}).get("GITHUB_TOKEN")
            or os.getenv("ARGA_GITHUB_TOKEN")
            or ""
        )
        if not token:
            raise RuntimeError(
                "Arga twin returned no GITHUB_TOKEN; set ARGA_GITHUB_TOKEN from the twin page in the Arga web app."
            )
        self._twin_api = self._twin_client_factory(self._base_url, token)
        self._ensure_repo()
        return self._twin_api

    def _ensure_repo(self) -> None:
        assert self._twin_api is not None
        owner, name = self._repo.split("/", 1)
        if self._twin_api.get(f"/repos/{owner}/{name}").status_code == 200:
            return
        r = self._twin_api.post("/user/repos", json={"name": name, "private": True, "auto_init": True})
        if r.status_code not in (200, 201, 422):
            r.raise_for_status()

    def close(self) -> None:
        if self._owns_run and self._run_id and self._twin_api is not None:
            try:
                self._api.post(TEARDOWN_PATH.format(run_id=self._run_id))
            except Exception:
                pass
        self._twin_api = None

    # ------------------------------------------------------------------ ledger
    def reset(self) -> None:
        self._ledger = []

    def request_count(self) -> int:
        return len(self._ledger)

    def ledger(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._ledger)

    def snapshot(self) -> dict[str, Any]:
        return {
            "request_count": self.request_count(),
            "ledger": self.ledger(),
            "state": self._twin_state() if self._twin_api is not None else {},
            "provider": self.provider,
            "twin": self._twin,
            "run_id": self._run_id,
        }

    def _twin_state(self) -> dict[str, Any]:
        """Independent evidence read back from the twin itself."""
        api = self._ensure_twin()
        owner, name = self._repo.split("/", 1)
        state: dict[str, Any] = {"repo": self._repo}
        c = api.get(f"/repos/{owner}/{name}/collaborators")
        state["collaborators"] = (
            [{"login": x.get("login"), "permissions": x.get("permissions")} for x in c.json()]
            if c.status_code == 200 else []
        )
        h = api.get(f"/repos/{owner}/{name}/hooks")
        state["hooks"] = (
            [{"id": x.get("id"), "url": (x.get("config") or {}).get("url")} for x in h.json()]
            if h.status_code == 200 else []
        )
        return state

    # --------------------------------------------------------------- execution
    def execute(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if tool_name not in _ALLOWED_TOOLS:
            raise ValueError(f"Tool is not mapped to the Arga twin: {tool_name}")
        params = _redact(dict(parameters))
        entry: dict[str, Any] = {
            "seq": len(self._ledger) + 1,
            "provider": self.provider,
            "tool_name": tool_name,
            "parameters": params,
            "status": "started",
        }
        self._ledger.append(entry)
        started = time.perf_counter()
        try:
            api = self._ensure_twin()
            state_before = self._twin_state()
            method, path, body = self._map(tool_name, parameters)
            r = api.request(method, path, json=body)
            if r.status_code >= 400:
                raise RuntimeError(f"twin returned {r.status_code}")
            state_after = self._twin_state()
        except Exception as exc:
            entry["status"] = "failed"
            entry["error"] = type(exc).__name__
            raise ToolExecutionError(
                "Arga twin execution failed; AgentJail did not fall back to local execution.",
                result={
                    "simulated": False,
                    "independent_ledger": True,
                    "provider": self.provider,
                    "sandbox_created": False,
                    "tool_name": tool_name,
                    "status": "failed",
                    "seq": entry["seq"],
                    "error": type(exc).__name__,
                },
            ) from exc
        entry.update({"status": "ok", "twin_request": f"{method} {path}", "http_status": r.status_code})
        return {
            "simulated": False,
            "independent_ledger": True,
            "provider": self.provider,
            "sandbox_created": True,
            "sandbox_id": self._run_id,
            "twin": self._twin,
            "twin_request": f"{method} {path}",
            "http_status": r.status_code,
            "tool_name": tool_name,
            "parameters": params,
            "status": "ok",
            "seq": entry["seq"],
            "state_before": state_before,
            "state_after": state_after,
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            "message": f"Arga {self._twin} twin executed {tool_name} as {method} {path}",
        }

    def _map(self, tool_name: str, p: dict[str, Any]) -> tuple[str, str, dict[str, Any] | None]:
        owner, name = self._repo.split("/", 1)
        if tool_name == "create_service_identity":
            role = str(p.get("role") or "temporary")
            login = str(p.get("name") or f"identity-{role}").replace(" ", "-")[:39]
            perm = "admin" if role.lower() in {"administrator", "admin", "cluster-admin"} else "push"
            return "PUT", f"/repos/{owner}/{name}/collaborators/{login}", {"permission": perm}
        if tool_name == "restart_service":
            service = str(p.get("service") or p.get("resource") or "unknown")
            return "POST", f"/repos/{owner}/{name}/dispatches", {
                "event_type": "restart_service",
                "client_payload": {"service": service, "blast_radius": p.get("blast_radius", "one_service")},
            }
        if tool_name == "post_webhook":
            return "POST", f"/repos/{owner}/{name}/hooks", {
                "name": "web",
                "config": {"url": str(p.get("destination") or p.get("url") or ""), "content_type": "json"},
                "events": ["push"],
            }
        raise ValueError(tool_name)
