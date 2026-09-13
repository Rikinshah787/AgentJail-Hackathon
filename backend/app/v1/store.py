from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import (
    ActorRow,
    AgentRow,
    ApprovalRow,
    DecisionRow,
    IncidentRow,
    PolicyRow,
    ScarRow,
    ToolCallRow,
    utcnow,
)
from .ids import new_id


def row_to_dict(row: Any) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if isinstance(value, datetime):
            data[column.name] = value.isoformat()
        else:
            data[column.name] = value
    return data


class Store:
    def __init__(self, session: Session) -> None:
        self.session = session

    def policies(self) -> list[dict[str, Any]]:
        return [row_to_dict(r) for r in self.session.scalars(select(PolicyRow)).all()]

    def scars(self) -> list[dict[str, Any]]:
        return [row_to_dict(r) for r in self.session.scalars(select(ScarRow)).all()]

    def agents(self) -> list[dict[str, Any]]:
        return [row_to_dict(r) for r in self.session.scalars(select(AgentRow)).all()]

    def get_scar(self, scar_id: str) -> ScarRow | None:
        return self.session.get(ScarRow, scar_id)

    def increment_scar_match(self, scar_id: str) -> None:
        scar = self.session.get(ScarRow, scar_id)
        if scar is None:
            return
        scar.match_count += 1
        scar.last_matched_at = utcnow()

    def set_scar_status(self, scar_id: str, status: str) -> ScarRow | None:
        scar = self.session.get(ScarRow, scar_id)
        if scar is None:
            return None
        scar.status = status
        return scar

    def create_candidate_scar(self, *, tool_name: str, source_type: str, reason: str) -> ScarRow:
        scar = ScarRow(
            id=new_id("scar"),
            name="Unverified privilege escalation",
            description=reason,
            status="under_review",
            attack_category="privilege_escalation",
            affected_tools=[tool_name],
            affected_sources=[source_type],
            indicators=["privilege_goal", "unverified_source", "identity_creation"],
            match_count=0,
            confidence=0.72,
            reviewed_by=None,
            expires_at=utcnow() + timedelta(days=90),
        )
        self.session.add(scar)
        return scar

    def save_tool_call(self, payload: dict[str, Any]) -> ToolCallRow:
        row = ToolCallRow(
            id=new_id("tc"),
            agent_id=payload["agent_id"],
            actor_id=payload["actor_id"],
            tool_name=payload["tool_name"],
            action=payload["action"],
            resource=payload["resource"],
            parameters=payload["parameters"],
            source=payload["source"],
            requested_at=utcnow(),
        )
        self.session.add(row)
        return row

    def save_decision(self, payload: dict[str, Any]) -> DecisionRow:
        row = DecisionRow(
            id=new_id("dec"),
            tool_call_id=payload["tool_call_id"],
            decision=payload["decision"],
            risk=payload["risk"],
            reason=payload["reason"],
            policy_ids=payload.get("policy_ids") or [],
            matched_scar_ids=payload.get("matched_scar_ids") or [],
            checks=payload.get("checks") or [],
            executed=payload.get("executed", False),
            execution_result=payload.get("execution_result"),
            decision_latency_ms=payload.get("decision_latency_ms") or 0,
            created_at=utcnow(),
        )
        self.session.add(row)
        return row

    def save_approval(self, *, decision_id: str, action: str, tool_call: dict[str, Any]) -> ApprovalRow:
        row = ApprovalRow(
            id=new_id("ap"),
            decision_id=decision_id,
            status="pending",
            requested_action=action,
            expires_at=utcnow() + timedelta(minutes=5),
            stored_tool_call=tool_call,
        )
        self.session.add(row)
        return row

    def get_approval(self, approval_id: str) -> ApprovalRow | None:
        return self.session.get(ApprovalRow, approval_id)

    def expire_stale_approvals(self) -> None:
        now = utcnow()
        pending = self.session.scalars(select(ApprovalRow).where(ApprovalRow.status == "pending")).all()
        for row in pending:
            expires = row.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires <= now:
                row.status = "expired"

    def approvals(self) -> list[dict[str, Any]]:
        self.expire_stale_approvals()
        rows = self.session.scalars(select(ApprovalRow).order_by(ApprovalRow.expires_at.desc())).all()
        out = []
        for row in rows:
            item = row_to_dict(row)
            decision = self.session.get(DecisionRow, row.decision_id)
            tool = self.session.get(ToolCallRow, decision.tool_call_id) if decision else None
            item["risk"] = decision.risk if decision else "high"
            item["reason"] = decision.reason if decision else ""
            item["agent_id"] = tool.agent_id if tool else ""
            item["source"] = tool.source if tool else {}
            item["actor_id"] = tool.actor_id if tool else ""
            actor = self.session.get(ActorRow, item["actor_id"]) if item["actor_id"] else None
            item["actor_name"] = actor.display_name if actor else item["actor_id"]
            item["agent_name"] = "SRE Agent"
            out.append(item)
        return out

    def save_incident(self, payload: dict[str, Any]) -> IncidentRow:
        row = IncidentRow(
            id=new_id("inc"),
            scenario=payload["scenario"],
            mode=payload["mode"],
            status=payload["status"],
            tool_call_id=payload.get("tool_call_id"),
            decision_id=payload.get("decision_id"),
            attack_variant=payload.get("attack_variant"),
            user_instruction=payload.get("user_instruction") or "",
            retrieved_content=payload.get("retrieved_content") or "",
            timeline=payload.get("timeline") or [],
            trace=payload.get("trace") or {},
            error=payload.get("error"),
            started_at=payload.get("started_at") or utcnow(),
            completed_at=payload.get("completed_at") or utcnow(),
        )
        self.session.add(row)
        return row

    def incidents(self) -> list[dict[str, Any]]:
        rows = self.session.scalars(select(IncidentRow).order_by(IncidentRow.started_at.desc())).all()
        return [self.incident_detail(row.id) for row in rows]

    def incident_detail(self, incident_id: str) -> dict[str, Any] | None:
        row = self.session.get(IncidentRow, incident_id)
        if row is None:
            return None
        data = row_to_dict(row)
        decision = self.session.get(DecisionRow, row.decision_id) if row.decision_id else None
        tool = self.session.get(ToolCallRow, row.tool_call_id) if row.tool_call_id else None
        data["decision"] = row_to_dict(decision) if decision else None
        data["tool_call"] = row_to_dict(tool) if tool else None
        return data

    def dashboard(self) -> dict[str, Any]:
        decisions = list(self.session.scalars(select(DecisionRow)).all())
        approvals = self.approvals()
        scars = list(self.session.scalars(select(ScarRow)).all())
        recent = []
        for dec in sorted(decisions, key=lambda d: d.created_at, reverse=True)[:3]:
            tool = self.session.get(ToolCallRow, dec.tool_call_id)
            recent.append(
                {
                    "id": dec.id,
                    "decision": dec.decision,
                    "title": dec.reason,
                    "reason": dec.reason,
                    "tool": tool.tool_name if tool else "",
                    "risk": dec.risk,
                    "created_at": dec.created_at.isoformat(),
                }
            )
        return {
            "attacks_blocked": sum(1 for d in decisions if d.decision == "deny"),
            "safe_allowed": sum(1 for d in decisions if d.decision == "allow" and d.executed),
            "awaiting_approval": sum(1 for a in approvals if a["status"] == "pending"),
            "scar_matches": sum(1 for d in decisions if d.matched_scar_ids),
            "incidents": len(list(self.session.scalars(select(IncidentRow)).all())),
            "recent_decisions": recent,
            "agent": "SRE Agent",
            "protection_active": True,
        }

    def commit(self) -> None:
        self.session.commit()
