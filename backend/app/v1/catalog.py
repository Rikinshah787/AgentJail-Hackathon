"""Tool sensitivity catalog — used by the deterministic engine, not by tools themselves."""

from __future__ import annotations

from typing import Literal

Sensitivity = Literal["low", "high", "critical"]

PRIVILEGED_IDENTITY_TOOLS = frozenset(
    {"create_service_identity", "grant_admin_role", "create_api_key"}
)
RESTART_TOOLS = frozenset({"restart_service"})
EXFIL_TOOLS = frozenset({"send_email", "upload_file", "post_webhook", "send_message"})
PHYSICAL_FINANCIAL_TOOLS = frozenset(
    {"unlock_door", "grant_guest_access", "transfer_money", "pay_bill", "purchase_item"}
)
CONTROL_PLANE = frozenset({"control-plane", "kube-apiserver", "etcd"})
CRITICAL_HINTS = ("admin", "delete", "destroy", "root", "iam", "cluster")
IDENTITY_ROLES = frozenset({"identity_manager", "iam_admin", "operator"})
SENSITIVE_PARAM_KEYS = frozenset(
    {"ssn", "password", "secret", "api_key", "pii", "retrieved_from_tool", "contains_sensitive_data"}
)


def tool_sensitivity(tool_name: str) -> Sensitivity:
    if tool_name in PRIVILEGED_IDENTITY_TOOLS or tool_name in PHYSICAL_FINANCIAL_TOOLS:
        return "critical"
    if tool_name in EXFIL_TOOLS:
        return "high"
    if tool_name in RESTART_TOOLS:
        return "low"
    lowered = tool_name.lower()
    if any(hint in lowered for hint in CRITICAL_HINTS):
        return "critical"
    return "high"


def privilege_goal(tool_name: str, parameters: dict) -> bool:
    if tool_name in PRIVILEGED_IDENTITY_TOOLS:
        return True
    role = str(parameters.get("role", "")).lower()
    return any(token in role for token in ("admin", "privileged", "elevated", "cluster"))


def urgency_or_bypass(text: str, parameters: dict) -> bool:
    blob = f"{text} {' '.join(str(v) for v in parameters.values())}".lower()
    return any(
        token in blob
        for token in (
            "urgent",
            "immediately",
            "cannot continue",
            "temporary",
            "short-lived",
            "break-glass",
            "bypass",
            "must create",
            "require creating",
        )
    )
