"""Development seed data for the AgentJail demo."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session  # noqa: TCH001

from .db import ActorRow, AgentRow, PolicyRow, ScarRow, utcnow

AGENT_ID = "sre-agent-01"
HUMAN_ID = "actor-human-jordan"
BOT_ID = "actor-incident-bot"
SCAR_PRIV = "scar-privilege-escalation"
SCAR_EXFIL = "scar-exfil-under-review"


def seed_if_empty(session: Session) -> None:
    if session.get(AgentRow, AGENT_ID):
        return
    seed(session)


def seed(session: Session) -> None:
    session.add(
        AgentRow(
            id=AGENT_ID,
            name="SRE Agent",
            framework="langgraph",
            status="protected",
            created_at=utcnow(),
        )
    )
    session.add_all(
        [
            ActorRow(
                id=HUMAN_ID,
                display_name="Jordan (verified operator)",
                actor_type="human",
                roles=["operator", "identity_manager"],
                verified=True,
            ),
            ActorRow(
                id=BOT_ID,
                display_name="Incident bot",
                actor_type="service",
                roles=["incident_reader"],
                verified=False,
            ),
        ]
    )
    now = utcnow()
    session.add_all(
        [
            PolicyRow(
                id="pol-privileged-identity",
                name="Privileged identity protection",
                description="If an agent tries to create a privileged identity, require a verified source and human approval.",
                enabled=True,
                tools=["create_service_identity", "grant_admin_role", "create_api_key"],
                risk_level="critical",
                require_verified_source=True,
                require_human_approval=True,
                allowed_roles=["operator", "identity_manager"],
                effect="approval_required",
            ),
            PolicyRow(
                id="pol-unverified-source",
                name="Unverified source block",
                description="If the instruction came from an unverified ticket, email, or website, block high-risk tools.",
                enabled=True,
                tools=["create_service_identity", "transfer_money", "unlock_door"],
                risk_level="critical",
                require_verified_source=True,
                require_human_approval=False,
                allowed_roles=[],
                effect="deny",
            ),
            PolicyRow(
                id="pol-safe-restart",
                name="Safe restart allowlist",
                description="Allow verified monitoring systems to restart known services with limited blast radius.",
                enabled=True,
                tools=["restart_service"],
                risk_level="low",
                require_verified_source=True,
                require_human_approval=False,
                allowed_roles=[],
                effect="allow",
            ),
            PolicyRow(
                id="pol-exfil",
                name="Sensitive data leaving the system",
                description="Do not send private data to an untrusted destination.",
                enabled=True,
                tools=["send_email", "upload_file", "post_webhook", "send_message"],
                risk_level="high",
                require_verified_source=True,
                require_human_approval=True,
                allowed_roles=["operator"],
                effect="approval_required",
            ),
        ]
    )
    session.add_all(
        [
            ScarRow(
                id=SCAR_PRIV,
                name="Unverified privilege escalation",
                description="Unverified content asked the agent to create an elevated identity.",
                status="active",
                attack_category="privilege_escalation",
                affected_tools=["create_service_identity", "grant_admin_role"],
                affected_sources=["ticket", "email", "agent_message"],
                indicators=["privilege_goal", "unverified_source", "urgency_or_bypass"],
                match_count=0,
                confidence=0.91,
                reviewed_by="Security on-call",
                created_at=now,
                expires_at=now + timedelta(days=90),
            ),
            ScarRow(
                id=SCAR_EXFIL,
                name="Hidden exfil via summary email",
                description="Candidate pattern for sending retrieved private data outside the system.",
                status="under_review",
                attack_category="exfiltration",
                affected_tools=["send_email", "upload_file"],
                affected_sources=["document", "website"],
                indicators=["external_destination_pattern"],
                match_count=0,
                confidence=0.64,
                reviewed_by=None,
                created_at=now,
                expires_at=now + timedelta(days=60),
            ),
        ]
    )
    session.commit()


def reset_and_seed(session: Session) -> None:
    from .db import ApprovalRow, DecisionRow, ImprovementRunRow, IncidentRow, ToolCallRow

    for model in (ImprovementRunRow, ApprovalRow, DecisionRow, IncidentRow, ToolCallRow, ScarRow, PolicyRow, ActorRow, AgentRow):
        for row in session.scalars(select(model)).all():
            session.delete(row)
    session.commit()
    seed(session)
