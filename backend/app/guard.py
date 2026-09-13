"""Fail-closed policy gate for Agent Jail — provenance + scar memory."""

from dataclasses import dataclass, field
from typing import Literal

Decision = Literal["allow", "deny", "approval_required"]


@dataclass(frozen=True)
class ToolCall:
    tool: str
    actor_id: str
    source: str
    source_verified: bool
    payload: dict[str, str]


@dataclass(frozen=True)
class Scar:
    pattern: str
    tool: str
    risk: Literal["high", "critical"]
    action: Literal["deny", "approval_required"]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class DecisionResult:
    decision: Decision
    risk: Literal["low", "high", "critical"]
    reason: str
    executed: bool
    matched_scar: bool
    scar_created: Scar | None = None


@dataclass
class Guard:
    scars: list[Scar] = field(default_factory=list)

    _PRIVILEGED_TOOLS = frozenset({"create_service_identity", "change_network_access", "rotate_secrets"})
    _CONTROL_PLANE = frozenset({"control-plane", "kube-apiserver", "etcd"})

    def evaluate(self, call: ToolCall) -> DecisionResult:
        scar = self._matching_scar(call)
        if scar is not None:
            return DecisionResult(
                decision=scar.action if scar.action == "deny" else "deny",
                risk="critical",
                reason=f"Scar match: {scar.pattern}",
                executed=False,
                matched_scar=True,
            )

        # Malicious restart of control-plane even if "verified" → deny + scar
        if call.tool == "restart_service":
            service = call.payload.get("service", "")
            if service in self._CONTROL_PLANE:
                created = Scar(
                    pattern="restart targeted control-plane blast radius",
                    tool=call.tool,
                    risk="critical",
                    action="deny",
                    evidence=(f"service={service}", f"source={call.source}"),
                )
                self.scars.append(created)
                return DecisionResult(
                    decision="deny",
                    risk="critical",
                    reason="Control-plane restart is outside autonomous SRE authority.",
                    executed=False,
                    matched_scar=False,
                    scar_created=created,
                )
            if call.source_verified and service.startswith("gpu-worker"):
                return DecisionResult(
                    decision="allow",
                    risk="low",
                    reason="Verified low-blast-radius service restart is within delegated authority.",
                    executed=True,
                    matched_scar=False,
                )
            if not call.source_verified:
                return DecisionResult(
                    decision="approval_required",
                    risk="high",
                    reason="Unverified restart request — operator must approve before execution.",
                    executed=False,
                    matched_scar=False,
                )

        # Privileged tools from unverified source → deny + scar
        if call.tool in self._PRIVILEGED_TOOLS and not call.source_verified:
            created = Scar(
                pattern="unverified source requested privileged infrastructure access",
                tool=call.tool,
                risk="critical",
                action="deny",
                evidence=(
                    f"source={call.source}",
                    "source_verified=false",
                    f"requested_role={call.payload.get('role', call.payload.get('secret', 'unknown'))}",
                ),
            )
            self.scars.append(created)
            return DecisionResult(
                decision="deny",
                risk="critical",
                reason="Privileged infrastructure actions require a verified source and human approval.",
                executed=False,
                matched_scar=False,
                scar_created=created,
            )

        # Verified privileged tools still need human approval (not auto-allow)
        if call.tool in self._PRIVILEGED_TOOLS and call.source_verified:
            return DecisionResult(
                decision="approval_required",
                risk="high",
                reason="Verified source, but privileged IAM/secrets changes require human approval.",
                executed=False,
                matched_scar=False,
            )

        return DecisionResult(
            decision="approval_required",
            risk="high",
            reason="Action is outside the demo agent's automatic authority; operator approval is required.",
            executed=False,
            matched_scar=False,
        )

    def _matching_scar(self, call: ToolCall) -> Scar | None:
        for scar in self.scars:
            if scar.pattern == "unverified source requested privileged infrastructure access":
                if not call.source_verified and call.tool in self._PRIVILEGED_TOOLS:
                    return scar
            if scar.pattern == "restart targeted control-plane blast radius":
                if call.tool == "restart_service" and call.payload.get("service") in self._CONTROL_PLANE:
                    return scar
        return None
