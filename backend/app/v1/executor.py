"""Independent mock tool server.

AgentJail must not be the sole witness of whether a tool ran.
This module owns the execution ledger and mutable sandbox state.
"""

from __future__ import annotations

import copy
from typing import Any, Protocol


class ToolExecutionError(RuntimeError):
    """A tool reached its executor but did not complete safely."""

    def __init__(self, message: str, *, result: dict[str, Any]) -> None:
        super().__init__(message)
        self.result = result


class ToolExecutor(Protocol):
    provider: str

    def execute(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]: ...

    def request_count(self) -> int: ...

    def ledger(self) -> list[dict[str, Any]]: ...

    def snapshot(self) -> dict[str, Any]: ...

    def reset(self) -> None: ...


class IndependentMockExecutor:
    """Hackathon-safe simulator with its own ledger.

    Proof rule: if AgentJail claims deny, this server must show zero new requests
    and unchanged state. AgentJail cannot forge that.
    """

    provider = "mock"

    def __init__(self) -> None:
        self._ledger: list[dict[str, Any]] = []
        self._state: dict[str, Any] = self._fresh_state()

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
            "request_count": self.request_count(),
            "ledger": self.ledger(),
            "state": copy.deepcopy(self._state),
        }

    def execute(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        entry = {
            "seq": len(self._ledger) + 1,
            "tool_name": tool_name,
            "parameters": dict(parameters),
        }
        self._ledger.append(entry)
        state_before = copy.deepcopy(self._state)
        self._apply(tool_name, parameters)
        return {
            "simulated": True,
            "independent_ledger": True,
            "provider": self.provider,
            "sandbox_created": False,
            "tool_name": tool_name,
            "parameters": dict(parameters),
            "status": "ok",
            "seq": entry["seq"],
            "state_before": state_before,
            "state_after": copy.deepcopy(self._state),
            "message": f"Independent mock executed {tool_name}",
        }

    def _apply(self, tool_name: str, parameters: dict[str, Any]) -> None:
        if tool_name == "create_service_identity":
            role = str(parameters.get("role") or "temporary")
            name = str(parameters.get("name") or f"identity-{role}")
            self._state["identities"][name] = role
            return
        if tool_name == "restart_service":
            service = str(parameters.get("service") or parameters.get("resource") or "")
            if service:
                self._state["services"][service] = "restarted"
            return
        if tool_name == "send_email":
            self._state["emails_sent"].append(dict(parameters))
            return
        if tool_name == "post_webhook":
            self._state["webhooks"].append(dict(parameters))
            return
        # Unknown tools still hit the ledger (proves reachability) but mark unknown.
        self._state.setdefault("unknown_executions", []).append(
            {"tool_name": tool_name, "parameters": dict(parameters)}
        )


# Back-compat alias used across the codebase.
MockExecutor = IndependentMockExecutor
