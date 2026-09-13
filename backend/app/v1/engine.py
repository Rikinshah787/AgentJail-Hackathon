"""Deterministic, explainable authorization engine.

This is the only authorization authority. An LLM must never make the final decision.
Fail closed: exceptions and unknown high-impact tools never return allow.
A scar match can raise risk but cannot independently authorize an action.
"""

from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable

from .catalog import (
    CONTROL_PLANE,
    EXFIL_TOOLS,
    IDENTITY_ROLES,
    PHYSICAL_FINANCIAL_TOOLS,
    PRIVILEGED_IDENTITY_TOOLS,
    RESTART_TOOLS,
    SENSITIVE_PARAM_KEYS,
    tool_sensitivity,
)
from .matcher import match_scars
from .schemas import AuthorizeRequest, CheckResult, Decision, Risk, ScarMatch

RISK_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _raise_risk(current: Risk, matched: bool) -> Risk:
    if not matched:
        return current
    order: list[Risk] = ["low", "medium", "high", "critical"]
    return order[min(3, order.index(current) + 1)]


def _sensitive_payload(parameters: dict[str, Any]) -> bool:
    if parameters.get("contains_sensitive_data") is True:
        return True
    if parameters.get("retrieved_from_tool"):
        return True
    return any(key in SENSITIVE_PARAM_KEYS for key in parameters)


def _destination_trust(parameters: dict[str, Any]) -> str:
    return str(parameters.get("destination_trust") or parameters.get("trust_level") or "untrusted")


def _blast_radius(parameters: dict[str, Any]) -> str:
    if parameters.get("blast_radius"):
        return str(parameters["blast_radius"])
    services = parameters.get("services")
    if isinstance(services, list) and len(services) > 1:
        return "multiple"
    return "one_service"


def _actor_can_request_identity(roles: list[str], actor_type: str, verified: bool) -> bool:
    if set(roles) & IDENTITY_ROLES:
        return True
    return actor_type == "human" and verified and "operator" in roles


PolicyFn = Callable[[AuthorizeRequest, list[dict[str, Any]]], tuple[Decision | None, list[str], list[CheckResult]]]


def evaluate_policies(request: AuthorizeRequest, policies: list[dict[str, Any]]) -> tuple[Decision | None, list[str], list[CheckResult]]:
    """Evaluate enabled policies. Extracted so tests can force an exception."""
    tool = request.tool_call.tool_name
    matched_ids: list[str] = []
    checks: list[CheckResult] = []
    for policy in policies:
        if not policy.get("enabled", True):
            continue
        tools = set(policy.get("tools") or [])
        if tools and tool not in tools:
            continue
        matched_ids.append(policy["id"])
        if policy.get("require_verified_source") and not request.source.verified:
            checks.append(
                CheckResult(
                    name=f"Policy:{policy.get('name')}",
                    status="failed",
                    explanation=policy.get("description") or "Verified source required.",
                )
            )
        if policy.get("require_human_approval"):
            checks.append(
                CheckResult(
                    name=f"Policy:{policy.get('name')}",
                    status="requires_approval",
                    explanation="This policy requires a human before execution.",
                )
            )
        allowed_roles = set(policy.get("allowed_roles") or [])
        if allowed_roles and not allowed_roles.intersection(request.actor.roles):
            checks.append(
                CheckResult(
                    name=f"Policy:{policy.get('name')}",
                    status="failed",
                    explanation="Actor role is outside the policy allowlist.",
                )
            )
    return None, matched_ids, checks


def authorize(
    request: AuthorizeRequest,
    *,
    policies: list[dict[str, Any]],
    scars: list[dict[str, Any]],
    now: datetime | None = None,
    policy_fn: PolicyFn = evaluate_policies,
) -> dict[str, Any]:
    """Return a decision dict. Never executes a tool."""
    started = datetime.now(timezone.utc)
    clock_start = perf_counter()
    now = now or started
    checks: list[CheckResult] = []
    try:
        return _authorize_inner(request, policies, scars, now, clock_start, policy_fn, checks)
    except Exception:
        # Fail closed: never allow if the policy engine faults.
        return {
            "decision": "deny",
            "risk": "critical",
            "reason": "Authorization engine failed closed. No action executed.",
            "policy_ids": [],
            "matched_scars": [],
            "checks": checks
            + [CheckResult(name="Engine", status="failed", explanation="Unexpected error; default is deny.")],
            "decision_latency_ms": _latency_ms(clock_start),
        }


def _latency_ms(clock_start: float) -> float:
    # perf_counter has sub-microsecond resolution; datetime.now() is ~1-15ms on Windows
    # and rounded every pure-Python decision down to 0ms.
    return round((perf_counter() - clock_start) * 1000, 3)


def _authorize_inner(
    request: AuthorizeRequest,
    policies: list[dict[str, Any]],
    scars: list[dict[str, Any]],
    now: datetime,
    clock_start: float,
    policy_fn: PolicyFn,
    checks: list[CheckResult],
) -> dict[str, Any]:
    tool = request.tool_call
    source = request.source
    actor = request.actor
    sensitivity = tool_sensitivity(tool.tool_name)
    content = " ".join(filter(None, [request.retrieved_content, request.user_instruction]))

    checks.append(
        CheckResult(
            name="Tool sensitivity",
            status=sensitivity,
            explanation=_sensitivity_explainer(tool.tool_name, sensitivity),
        )
    )

    if source.verified:
        checks.append(
            CheckResult(
                name="Source verification",
                status="passed",
                explanation=f"{source.display_name} is a verified {source.source_type}.",
            )
        )
    else:
        checks.append(
            CheckResult(
                name="Source verification",
                status="failed",
                explanation=f"{source.display_name} was not verified.",
            )
        )

    identity_ok = _actor_can_request_identity(actor.roles, actor.actor_type, actor.verified)
    if tool.tool_name in PRIVILEGED_IDENTITY_TOOLS and not identity_ok:
        checks.append(
            CheckResult(
                name="Actor permission",
                status="failed",
                explanation="The requesting actor does not have identity-management permission.",
            )
        )
    else:
        checks.append(
            CheckResult(
                name="Actor permission",
                status="passed" if actor.roles else "limited",
                explanation="Actor roles were checked against the requested tool.",
            )
        )

    try:
        _forced, policy_ids, policy_checks = policy_fn(request, policies)
    except Exception:
        return {
            "decision": "deny",
            "risk": "critical",
            "reason": "Policy evaluation failed closed. No action executed.",
            "policy_ids": [],
            "matched_scars": [],
            "checks": checks
            + [CheckResult(name="Policy engine", status="failed", explanation="Exception during policy evaluation.")],
            "decision_latency_ms": _latency_ms(clock_start),
        }
    checks.extend(policy_checks)

    matched = match_scars(scars=scars, tool=tool, source=source, content=content, now=now)
    if matched:
        checks.append(
            CheckResult(
                name="Scar match",
                status="matched",
                explanation=matched[0].explanation + " Scar match increased risk. Policy made the final decision.",
            )
        )
    else:
        checks.append(
            CheckResult(
                name="Scar match",
                status="none",
                explanation="No active, non-expired scar matched this behavior.",
            )
        )

    decision, risk, reason = _apply_rules(request, sensitivity, identity_ok)
    risk = _raise_risk(risk, bool(matched))
    # Scar matches never flip a deny/approval into allow.
    if decision == "allow" and matched and tool.tool_name in PRIVILEGED_IDENTITY_TOOLS:
        decision = "approval_required"
        reason = "Scar match increased risk. A human must still approve this privileged action."

    if decision == "approval_required":
        checks.append(
            CheckResult(
                name="Human approval",
                status="required",
                explanation="A human must approve this exact action before it can run.",
            )
        )
    elif decision == "deny":
        checks.append(
            CheckResult(
                name="Human approval",
                status="missing",
                explanation="The action was blocked before a human review was possible.",
            )
        )
    else:
        checks.append(
            CheckResult(
                name="Human approval",
                status="not_required",
                explanation="Verified, limited-blast-radius action does not need a human.",
            )
        )

    return {
        "decision": decision,
        "risk": risk,
        "reason": reason,
        "policy_ids": policy_ids,
        "matched_scars": [m.model_dump() if isinstance(m, ScarMatch) else m for m in matched],
        "checks": [c.model_dump() if isinstance(c, CheckResult) else c for c in checks],
        "decision_latency_ms": _latency_ms(clock_start),
    }


def _sensitivity_explainer(tool_name: str, sensitivity: str) -> str:
    if tool_name in PRIVILEGED_IDENTITY_TOOLS:
        return "Creating a privileged identity can grant persistent access."
    if tool_name in PHYSICAL_FINANCIAL_TOOLS:
        return "Physical or financial actions can cause real-world harm."
    if tool_name in EXFIL_TOOLS:
        return "This tool can send data outside the protected environment."
    if sensitivity == "critical":
        return "Unknown high-impact tool — fail closed."
    if tool_name in RESTART_TOOLS:
        return "Service restart has limited blast radius when scoped to one service."
    return "This tool can change production state."


def _apply_rules(request: AuthorizeRequest, sensitivity: str, identity_ok: bool) -> tuple[Decision, Risk, str]:
    tool = request.tool_call
    source = request.source
    name = tool.tool_name
    params = tool.parameters

    # Rule 1 — privileged identity creation. Never automatically allow.
    if name in PRIVILEGED_IDENTITY_TOOLS:
        if not source.verified:
            return (
                "deny",
                "critical",
                "An unverified ticket attempted to create a privileged identity."
                if source.source_type == "ticket"
                else "An unverified source attempted to create a privileged identity.",
            )
        return (
            "approval_required",
            "high",
            "A verified operator requested a privileged identity. A human must approve this.",
        )

    # Rule 2 — low-risk service restart
    if name in RESTART_TOOLS:
        service = str(params.get("service") or params.get("resource") or "")
        if service in CONTROL_PLANE:
            return (
                "deny",
                "critical",
                "Restarting the control plane is outside autonomous agent authority.",
            )
        if not source.verified:
            return ("deny", "high", "An unverified source tried to restart a service.")
        if _blast_radius(params) != "one_service":
            return (
                "approval_required",
                "medium",
                "Restarting more than one service needs a human.",
            )
        return (
            "allow",
            "low",
            "Verified source and limited blast radius — the restart is allowed.",
        )

    # Rule 3 — sensitive data leaving the system
    if name in EXFIL_TOOLS and _sensitive_payload(params):
        dest_trust = _destination_trust(params)
        if dest_trust == "allowed":
            return ("allow", "medium", "An explicit policy allows this exact destination.")
        if dest_trust in {"verified", "trusted"} and source.verified:
            return (
                "approval_required",
                "high",
                "Sensitive data is going to an external but verified destination. A human must approve this.",
            )
        return (
            "deny",
            "critical",
            "Sensitive data would be sent to an untrusted destination.",
        )

    # Rule 4 — physical or financial
    if name in PHYSICAL_FINANCIAL_TOOLS:
        if not source.verified:
            return ("deny", "critical", "An unverified source tried to take a physical or financial action.")
        return (
            "approval_required",
            "critical",
            "Physical and financial actions always need a human.",
        )

    # Rule 5 — default fail-closed
    if sensitivity == "critical":
        return ("deny", "critical", "Unknown critical action — AgentJail failed closed.")
    return (
        "approval_required",
        "high" if sensitivity == "high" else "medium",
        "No specific policy allows this action yet. A human must approve it.",
    )
