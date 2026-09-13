"""Ephemeral CoreWeave Sandbox executor for allowed AgentJail tool calls.

The W&B credential authenticates the host SDK to the sandbox gateway. It is
never injected into the sandbox. Model-controlled parameters are serialized as
data and consumed by a fixed Python runner; they never become shell source.
"""

from __future__ import annotations

import base64
import copy
import json
import time
from typing import Any

from .executor import ToolExecutionError

_ALLOWED_TOOLS = frozenset(
    {
        "create_service_identity",
        "restart_service",
        "send_email",
        "post_webhook",
    }
)
_MAX_PAYLOAD_BYTES = 16 * 1024
_MAX_OUTPUT_CHARS = 2_000

# Fixed runner: the tool name is allowlisted on the host and the payload is
# decoded as JSON data. No shell is involved and no external service is called.
_SANDBOX_RUNNER = r"""
import base64
import json
import sys

tool = sys.argv[1]
parameters = json.loads(base64.urlsafe_b64decode(sys.argv[2]).decode("utf-8"))

if tool == "restart_service":
    service = str(parameters.get("service") or parameters.get("resource") or "unknown")
    output = {"status": "ok", "effect": f"{service} restarted", "service": service}
elif tool == "create_service_identity":
    role = str(parameters.get("role") or "temporary")
    name = str(parameters.get("name") or f"identity-{role}")
    output = {"status": "ok", "effect": "sandbox identity created", "identity": name, "role": role}
elif tool == "send_email":
    output = {"status": "ok", "effect": "sandbox email recorded", "recipient": str(parameters.get("to") or "")}
elif tool == "post_webhook":
    output = {"status": "ok", "effect": "sandbox webhook recorded", "destination": str(parameters.get("destination") or "")}
else:
    raise SystemExit("tool not allowlisted")

print(json.dumps(output, separators=(",", ":")))
""".strip()


def _safe_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    """Return a bounded JSON value without logging credential-shaped fields."""
    encoded = json.dumps(parameters, separators=(",", ":"), sort_keys=True)
    if len(encoded.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
        raise ValueError("Tool parameters exceed the sandbox payload limit.")
    decoded = json.loads(encoded)
    if not isinstance(decoded, dict):
        raise ValueError("Tool parameters must be a JSON object.")
    return decoded


def _redacted_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    sensitive = {"api_key", "password", "secret", "token", "authorization"}
    return {
        str(key): "[REDACTED]" if str(key).lower() in sensitive else value
        for key, value in parameters.items()
    }


def _bounded_text(value: Any) -> str:
    text = str(value or "")
    return text[:_MAX_OUTPUT_CHARS]


class CoreWeaveSandboxExecutor:
    """Run each allowed call in a short-lived, network-isolated sandbox."""

    provider = "coreweave_sandbox"

    def __init__(
        self,
        *,
        sandbox_cls: Any | None = None,
        auth_strategy: Any | None = None,
        network_options_cls: Any | None = None,
    ) -> None:
        if sandbox_cls is None or auth_strategy is None or network_options_cls is None:
            try:
                from cwsandbox import AuthStrategy, NetworkOptions, Sandbox
            except ImportError as exc:
                raise RuntimeError(
                    'CoreWeave executor requires: pip install "cwsandbox[wandb]==1.14.2"'
                ) from exc
            sandbox_cls = sandbox_cls or Sandbox
            auth_strategy = auth_strategy or AuthStrategy
            network_options_cls = network_options_cls or NetworkOptions
        self._sandbox_cls = sandbox_cls
        self._auth_strategy = auth_strategy
        self._network_options_cls = network_options_cls
        self._ledger: list[dict[str, Any]] = []
        self._state = self._fresh_state()

    @staticmethod
    def _fresh_state() -> dict[str, Any]:
        return {
            "identities": {},
            "services": {
                "gpu-worker-3": "running",
                "gpu-worker-12": "running",
                "api-gateway": "running",
            },
            "emails_sent": [],
            "webhooks": [],
        }

    def reset(self) -> None:
        self._ledger = []
        self._state = self._fresh_state()

    def request_count(self) -> int:
        return len(self._ledger)

    def ledger(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._ledger)

    def snapshot(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "request_count": self.request_count(),
            "ledger": self.ledger(),
            "state": copy.deepcopy(self._state),
        }

    def execute(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if tool_name not in _ALLOWED_TOOLS:
            raise ValueError(f"Tool is not allowlisted for sandbox execution: {tool_name}")
        safe_parameters = _safe_parameters(parameters)
        payload = base64.urlsafe_b64encode(
            json.dumps(safe_parameters, separators=(",", ":")).encode("utf-8")
        ).decode("ascii")
        entry: dict[str, Any] = {
            "seq": len(self._ledger) + 1,
            "provider": self.provider,
            "tool_name": tool_name,
            "parameters": _redacted_parameters(safe_parameters),
            "status": "started",
            "sandbox_created": False,
        }
        self._ledger.append(entry)
        started = time.perf_counter()
        sandbox_id: str | None = None
        try:
            with self._sandbox_cls.run(
                auth=self._auth_strategy.WANDB,
                container_image="python:3.12-slim",
                max_lifetime_seconds=120,
                network=self._network_options_cls(deny_egress=True, deny_ingress=True),
                resources={"cpu": "500m", "memory": "512Mi"},
                tags=["agentjail", "hackathon"],
            ) as sandbox:
                sandbox_id = str(getattr(sandbox, "sandbox_id", "") or "") or None
                entry["sandbox_created"] = True
                entry["sandbox_id"] = sandbox_id
                process_result = sandbox.exec(
                    ["python", "-c", _SANDBOX_RUNNER, tool_name, payload],
                    timeout_seconds=30,
                    check=True,
                ).result()
            stdout = _bounded_text(getattr(process_result, "stdout", ""))
            stderr = _bounded_text(getattr(process_result, "stderr", ""))
            returncode = int(getattr(process_result, "returncode", 1))
            if returncode != 0:
                raise RuntimeError("Sandbox command returned a non-zero status.")
            parsed = json.loads(stdout.strip().splitlines()[-1]) if stdout.strip() else {}
            if not isinstance(parsed, dict):
                raise RuntimeError("Sandbox returned an invalid result.")
            self._apply(tool_name, safe_parameters)
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            entry.update({"status": "ok", "returncode": returncode, "duration_ms": duration_ms})
            return {
                "simulated": True,
                "independent_ledger": True,
                "provider": self.provider,
                "sandbox_created": True,
                "sandbox_id": sandbox_id,
                "tool_name": tool_name,
                "status": "ok",
                "returncode": returncode,
                "duration_ms": duration_ms,
                "stdout": parsed,
                "stderr": stderr,
                "message": f"CoreWeave Sandbox executed {tool_name}",
            }
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            entry.update(
                {
                    "status": "failed",
                    "sandbox_created": bool(entry.get("sandbox_created")),
                    "sandbox_id": sandbox_id,
                    "duration_ms": duration_ms,
                    "error_type": type(exc).__name__,
                }
            )
            raise ToolExecutionError(
                "CoreWeave sandbox execution failed closed.",
                result={
                    "simulated": True,
                    "provider": self.provider,
                    "sandbox_created": bool(entry.get("sandbox_created")),
                    "sandbox_id": sandbox_id,
                    "tool_name": tool_name,
                    "status": "failed",
                    "duration_ms": duration_ms,
                    "error": "CoreWeave sandbox execution failed closed.",
                },
            ) from exc

    def _apply(self, tool_name: str, parameters: dict[str, Any]) -> None:
        if tool_name == "create_service_identity":
            role = str(parameters.get("role") or "temporary")
            name = str(parameters.get("name") or f"identity-{role}")
            self._state["identities"][name] = role
        elif tool_name == "restart_service":
            service = str(parameters.get("service") or parameters.get("resource") or "")
            if service:
                self._state["services"][service] = "restarted"
        elif tool_name == "send_email":
            self._state["emails_sent"].append(_redacted_parameters(parameters))
        elif tool_name == "post_webhook":
            self._state["webhooks"].append(_redacted_parameters(parameters))
