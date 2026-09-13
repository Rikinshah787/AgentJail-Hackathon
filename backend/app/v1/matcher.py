"""Deterministic weighted scar matching. Scars raise risk; they never authorize."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .catalog import EXFIL_TOOLS, PRIVILEGED_IDENTITY_TOOLS, privilege_goal, urgency_or_bypass
from .schemas import ScarMatch, SourceIn, ToolCallIn


def _expired(expires_at: str | None, now: datetime) -> bool:
    if not expires_at:
        return False
    raw = expires_at.replace("Z", "+00:00")
    stamp = datetime.fromisoformat(raw)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp <= now


def match_scars(
    *,
    scars: list[dict[str, Any]],
    tool: ToolCallIn,
    source: SourceIn,
    content: str,
    now: datetime,
) -> list[ScarMatch]:
    matches: list[ScarMatch] = []
    for scar in scars:
        if scar.get("status") != "active":
            continue
        if _expired(scar.get("expires_at"), now):
            continue
        score = 0.0
        indicators: list[str] = []

        affected_tools = set(scar.get("affected_tools") or [])
        if tool.tool_name in affected_tools:
            score += 0.3
            indicators.append("same_sensitive_tool")
        elif tool.tool_name in PRIVILEGED_IDENTITY_TOOLS and affected_tools & PRIVILEGED_IDENTITY_TOOLS:
            score += 0.25
            indicators.append("same_tool_category")
        elif tool.tool_name in EXFIL_TOOLS and affected_tools & EXFIL_TOOLS:
            score += 0.25
            indicators.append("same_tool_category")

        if privilege_goal(tool.tool_name, tool.parameters):
            score += 0.25
            indicators.append("privilege_goal")

        affected_sources = set(scar.get("affected_sources") or [])
        if not source.verified and (source.source_type in affected_sources or not affected_sources):
            score += 0.25
            indicators.append("unverified_source_category")

        dest = str(tool.parameters.get("destination") or tool.parameters.get("to") or "")
        dest_patterns = scar.get("indicators") or []
        if dest and any("destination" in str(ind) or dest in str(ind) for ind in dest_patterns):
            score += 0.1
            indicators.append("external_destination_pattern")

        if urgency_or_bypass(content, tool.parameters):
            score += 0.1
            indicators.append("urgency_or_bypass")

        if score >= 0.6:
            matches.append(
                ScarMatch(
                    scar_id=scar["id"],
                    name=scar.get("name", "Matched scar"),
                    score=round(score, 3),
                    matched_indicators=indicators,
                    explanation=(
                        f"Matched security scar '{scar.get('name')}' on behavior, not wording. "
                        f"Indicators: {', '.join(indicators)}."
                    ),
                )
            )
    return matches
