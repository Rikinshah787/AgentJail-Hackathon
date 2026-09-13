"""Central authorization boundary.

decision = authorize(tool_call)
if decision.decision == "allow":
    result = mock_executor.execute(tool_call)
    decision.executed = True
else:
    result = None
    decision.executed = False
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .db import utcnow
from .engine import authorize as engine_authorize
from .executor import MockExecutor, ToolExecutionError, ToolExecutor
from .ids import new_id
from .schemas import AuthorizeRequest, AuthorizeResponse, CheckResult, ScarMatch
from .serialize import to_plain
from .store import Store
from .tracing import trace_authorize, trace_agent_action


class Gateway:
    def __init__(self, store: Store, executor: ToolExecutor | None = None) -> None:
        self.store = store
        self.executor = executor or MockExecutor()

    def authorize(self, request: AuthorizeRequest, *, execute: bool = True) -> AuthorizeResponse:
        # Authorization happens here — never inside a tool implementation.
        outcome = engine_authorize(
            request,
            policies=self.store.policies(),
            scars=self.store.scars(),
        )
        source = request.source.model_dump()
        if not source.get("id"):
            source["id"] = new_id("src")
        tool_row = self.store.save_tool_call(
            {
                "agent_id": request.agent_id,
                "actor_id": request.actor.id,
                "tool_name": request.tool_call.tool_name,
                "action": request.tool_call.action,
                "resource": request.tool_call.resource,
                "parameters": request.tool_call.parameters,
                "source": source,
            }
        )
        before_n = self.executor.request_count()
        before_state = self.executor.snapshot()["state"]
        executed = False
        execution_result: dict[str, Any] | None = {
            "provider": self.executor.provider,
            "sandbox_created": False,
            "status": "not_invoked",
            "reason": (
                "Executor invocation was disabled for this authorization check."
                if not execute
                else "Authorization did not allow executor invocation."
            ),
        }
        if execute and outcome["decision"] == "allow":
            try:
                execution_result = self.executor.execute(
                    request.tool_call.tool_name, request.tool_call.parameters
                )
                # Independent ledger is the source of truth — not this assignment alone.
                executed = (
                    self.executor.request_count() == before_n + 1
                    and execution_result.get("status") == "ok"
                )
            except ToolExecutionError as exc:
                # Preserve the authorization decision while proving execution
                # failed closed. Never fall back to a local executor.
                execution_result = exc.result
        after_n = self.executor.request_count()
        state_changed = self.executor.snapshot()["state"] != before_state
        matched = outcome.get("matched_scars") or []
        matched_ids = [m["scar_id"] if isinstance(m, dict) else m.scar_id for m in matched]
        for match in matched:
            self.store.increment_scar_match(match["scar_id"] if isinstance(match, dict) else match.scar_id)
        if outcome["decision"] == "deny" and request.tool_call.tool_name == "create_service_identity":
            existing = [s for s in self.store.scars() if s["status"] == "under_review" and "create_service_identity" in (s.get("affected_tools") or [])]
            if not existing:
                self.store.create_candidate_scar(
                    tool_name=request.tool_call.tool_name,
                    source_type=request.source.source_type,
                    reason=outcome["reason"],
                )
        decision_row = self.store.save_decision(
            {
                "tool_call_id": tool_row.id,
                "decision": outcome["decision"],
                "risk": outcome["risk"],
                "reason": outcome["reason"],
                "policy_ids": outcome.get("policy_ids") or [],
                "matched_scar_ids": matched_ids,
                "checks": to_plain(outcome.get("checks") or []),
                "executed": executed,
                "execution_result": execution_result,
                "decision_latency_ms": outcome.get("decision_latency_ms") or 0,
            }
        )
        if outcome["decision"] == "approval_required":
            self.store.save_approval(
                decision_id=decision_row.id,
                action=f"{request.tool_call.action} {request.tool_call.resource}",
                tool_call={
                    "id": tool_row.id,
                    "agent_id": request.agent_id,
                    "actor_id": request.actor.id,
                    "tool_name": request.tool_call.tool_name,
                    "action": request.tool_call.action,
                    "resource": request.tool_call.resource,
                    "parameters": request.tool_call.parameters,
                    "source": source,
                },
            )
        self.store.commit()
        trace_authorize(
            tool_name=request.tool_call.tool_name,
            decision=outcome["decision"],
            risk=outcome["risk"],
            reason=outcome["reason"],
            executed=executed,
            executor_requests=after_n - before_n,
            state_changed=state_changed,
            agent_id=request.agent_id,
            source_verified=request.source.verified,
            matched_scars=matched_ids,
            scenario="gateway.authorize",
            checks=to_plain(outcome.get("checks") or []),
            executor_provider=str(execution_result.get("provider") or self.executor.provider),
            sandbox_created=bool(execution_result.get("sandbox_created")),
            sandbox_id=execution_result.get("sandbox_id"),
            execution_status=str(execution_result.get("status") or "unknown"),
            execution_duration_ms=execution_result.get("duration_ms"),
        )
        user_msg = request.user_instruction or request.retrieved_content or request.tool_call.tool_name
        trace_agent_action(
            agent_name="SRE Agent",
            conversation_id=f"aj-{request.agent_id}",
            conversation_name=f"AgentJail · {request.agent_id}",
            user_message=str(user_msg)[:500],
            tool_name=request.tool_call.tool_name,
            tool_parameters=dict(request.tool_call.parameters or {}),
            decision=outcome["decision"],
            reason=outcome["reason"],
            executed=executed,
            executor_requests=after_n - before_n,
            state_changed=state_changed,
        )
        return AuthorizeResponse(
            id=decision_row.id,
            tool_call_id=tool_row.id,
            decision=outcome["decision"],
            risk=outcome["risk"],
            reason=outcome["reason"],
            executed=executed,
            checks=[CheckResult.model_validate(c) if isinstance(c, dict) else c for c in to_plain(outcome.get("checks") or [])],
            matched_scars=[ScarMatch.model_validate(m) if isinstance(m, dict) else m for m in matched],
            policy_ids=outcome.get("policy_ids") or [],
            decision_latency_ms=outcome.get("decision_latency_ms") or 0,
            created_at=decision_row.created_at if decision_row.created_at.tzinfo else decision_row.created_at.replace(tzinfo=timezone.utc),
            execution_result=execution_result,
        )

    def resolve_approval(
        self,
        approval_id: str,
        *,
        approve: bool,
        reviewer: str,
        review_reason: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.store.expire_stale_approvals()
        row = self.store.get_approval(approval_id)
        if row is None:
            raise KeyError("approval_not_found")
        if row.status != "pending":
            raise PermissionError("approval_not_pending")
        expires = row.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= utcnow():
            row.status = "expired"
            self.store.commit()
            raise PermissionError("approval_expired")
        stored = row.stored_tool_call or {}
        if parameters is not None and parameters != stored.get("parameters"):
            raise PermissionError("parameters_changed")
        row.reviewer = reviewer
        row.review_reason = review_reason
        row.resolved_at = utcnow()
        executed = False
        execution_result = None
        if approve:
            row.status = "approved"
            before_n = self.executor.request_count()
            try:
                execution_result = self.executor.execute(
                    stored["tool_name"], stored.get("parameters") or {}
                )
                executed = (
                    self.executor.request_count() == before_n + 1
                    and execution_result.get("status") == "ok"
                )
            except ToolExecutionError as exc:
                execution_result = exc.result
        else:
            row.status = "denied"
        from .db import DecisionRow

        decision = self.store.session.get(DecisionRow, row.decision_id)
        if decision is not None:
            decision.executed = executed
            decision.execution_result = execution_result
        self.store.commit()
        return {
            "id": row.id,
            "status": row.status,
            "executed": executed,
            "execution_result": execution_result,
            "reviewer": reviewer,
            "review_reason": review_reason,
        }
