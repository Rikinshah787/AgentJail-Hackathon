"""SQLite persistence for the AgentJail gateway."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

_DEFAULT = Path(__file__).resolve().parents[2] / "data" / "agentjail.db"


def database_url() -> str:
    return os.getenv("AGENTJAIL_DB", f"sqlite:///{_DEFAULT}")


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentRow(Base):
    __tablename__ = "agents"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    framework: Mapped[str] = mapped_column(String, default="custom")
    status: Mapped[str] = mapped_column(String, default="protected")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ActorRow(Base):
    __tablename__ = "actors"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String)
    actor_type: Mapped[str] = mapped_column(String)
    roles: Mapped[list] = mapped_column(JSON, default=list)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class PolicyRow(Base):
    __tablename__ = "policies"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    tools: Mapped[list] = mapped_column(JSON, default=list)
    risk_level: Mapped[str] = mapped_column(String, default="high")
    require_verified_source: Mapped[bool] = mapped_column(Boolean, default=True)
    require_human_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    allowed_roles: Mapped[list] = mapped_column(JSON, default=list)
    effect: Mapped[str] = mapped_column(String, default="approval_required")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ScarRow(Base):
    __tablename__ = "scars"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="under_review")
    attack_category: Mapped[str] = mapped_column(String)
    affected_tools: Mapped[list] = mapped_column(JSON, default=list)
    affected_sources: Mapped[list] = mapped_column(JSON, default=list)
    indicators: Mapped[list] = mapped_column(JSON, default=list)
    match_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    reviewed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ToolCallRow(Base):
    __tablename__ = "tool_calls"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_id: Mapped[str] = mapped_column(String)
    actor_id: Mapped[str] = mapped_column(String)
    tool_name: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    resource: Mapped[str] = mapped_column(String)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[dict] = mapped_column(JSON, default=dict)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DecisionRow(Base):
    __tablename__ = "decisions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tool_call_id: Mapped[str] = mapped_column(String)
    decision: Mapped[str] = mapped_column(String)
    risk: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(Text)
    policy_ids: Mapped[list] = mapped_column(JSON, default=list)
    matched_scar_ids: Mapped[list] = mapped_column(JSON, default=list)
    checks: Mapped[list] = mapped_column(JSON, default=list)
    executed: Mapped[bool] = mapped_column(Boolean, default=False)
    execution_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    decision_latency_ms: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApprovalRow(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    decision_id: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")
    requested_action: Mapped[str] = mapped_column(String)
    reviewer: Mapped[str | None] = mapped_column(String, nullable=True)
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stored_tool_call: Mapped[dict] = mapped_column(JSON, default=dict)


class IncidentRow(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    scenario: Mapped[str] = mapped_column(String)
    mode: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    tool_call_id: Mapped[str | None] = mapped_column(String, nullable=True)
    decision_id: Mapped[str | None] = mapped_column(String, nullable=True)
    attack_variant: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_instruction: Mapped[str] = mapped_column(Text, default="")
    retrieved_content: Mapped[str] = mapped_column(Text, default="")
    timeline: Mapped[list] = mapped_column(JSON, default=list)
    trace: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def make_engine(url: str | None = None):
    resolved = url or database_url()
    if resolved.startswith("sqlite:///"):
        path = resolved.replace("sqlite:///", "", 1)
        if path not in {":memory:", ""}:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(resolved, connect_args={"check_same_thread": False}, future=True)


def make_session_factory(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
