"""Pydantic API models for the AgentJail authorization gateway."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Decision = Literal["allow", "deny", "approval_required"]
Risk = Literal["low", "medium", "high", "critical"]
ActorType = Literal["human", "agent", "service"]
SourceType = Literal["ticket", "email", "alert", "document", "website", "agent_message", "api"]
ScarStatus = Literal["active", "under_review", "expired", "inactive"]
ApprovalStatus = Literal["pending", "approved", "denied", "expired"]
DemoScenario = Literal[
    "unprotected_poisoned_ticket",
    "protected_poisoned_ticket",
    "mutated_replay",
    "legitimate_sensitive_request",
]


class ActorIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    display_name: str | None = None
    actor_type: ActorType
    roles: list[str] = Field(default_factory=list)
    verified: bool = False


class SourceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    source_type: SourceType
    display_name: str
    verified: bool
    verification_method: str | None = None
    trust_level: str = "untrusted"
    raw_reference: str | None = None


class ToolCallIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str
    action: str
    resource: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class AuthorizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str
    actor: ActorIn
    source: SourceIn
    tool_call: ToolCallIn
    retrieved_content: str | None = None
    user_instruction: str | None = None


class CheckResult(BaseModel):
    name: str
    status: str
    explanation: str


class ScarMatch(BaseModel):
    scar_id: str
    name: str
    score: float
    matched_indicators: list[str]
    explanation: str


class AuthorizeResponse(BaseModel):
    id: str
    tool_call_id: str
    decision: Decision
    risk: Risk
    reason: str
    executed: bool
    checks: list[CheckResult]
    matched_scars: list[ScarMatch]
    policy_ids: list[str]
    decision_latency_ms: float
    created_at: datetime
    execution_result: dict[str, Any] | None = None


class ApprovalActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewer: str = "demo-reviewer"
    review_reason: str
    parameters: dict[str, Any] | None = None


class DemoRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: DemoScenario


class ImprovementRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_iterations: int = Field(default=3, ge=1, le=5)
    min_unique_variants: int = Field(default=2, ge=1, le=5)


class ImprovementReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewer: str = Field(min_length=1, max_length=120)
    review_reason: str = Field(min_length=1, max_length=1000)
