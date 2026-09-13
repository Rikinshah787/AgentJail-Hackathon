"""In-app ARIA coach for Agent Jail.

Official Ask ARIA lives in the W&B UI (no public chat HTTP API). With
WANDB_API_KEY we run the same analysis here via W&B Inference against the
live session ledger + Weave project context, and return a judge-facing report
in the demo UI.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .guard import DecisionResult, ToolCall
from .observability import weave_enabled


@dataclass
class SessionEvent:
    scenario: str
    mode: str
    tool: str
    decision: str
    risk: str
    reason: str
    executed: bool
    matched_scar: bool
    scar_created: bool
    at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_SESSION: list[SessionEvent] = []

_FAIL_LABELS = {
    "ungated_privilege_execution": "Ungated privilege execution (God mode ran IAM without a gate)",
    "scar_reopen_attempt": "Scar reopen attempt (mutated attack hit old memory)",
    "unverified_privilege_request": "Unverified privilege request (ticket/message without signed provenance)",
    "needs_human_approval": "Needs human approval (privileged but verified)",
    "insufficient_data": "Not enough demo events yet",
}


def clear_session() -> None:
    _SESSION.clear()


def record_session_event(
    *,
    scenario: str,
    mode: str,
    call: ToolCall,
    result: DecisionResult,
) -> SessionEvent:
    event = SessionEvent(
        scenario=scenario,
        mode=mode,
        tool=call.tool,
        decision=result.decision,
        risk=result.risk,
        reason=result.reason,
        executed=result.executed,
        matched_scar=result.matched_scar,
        scar_created=result.scar_created is not None,
    )
    _SESSION.append(event)
    return event


def weave_project() -> str:
    return os.getenv("WEAVE_PROJECT", "rshah88-arizona-state-university/agent-jail")


def weave_project_url() -> str:
    project = weave_project()
    if "/" not in project:
        return f"https://wandb.ai/{project}"
    entity, name = project.split("/", 1)
    return f"https://wandb.ai/{entity}/{name}/weave"


def api_key_ready() -> bool:
    return bool(os.getenv("WANDB_API_KEY"))


def _dominant_fail_mode(events: list[SessionEvent]) -> tuple[str, int]:
    counts: Counter[str] = Counter()
    for event in events:
        if event.mode == "god" and event.executed and event.tool != "restart_service":
            counts["ungated_privilege_execution"] += 1
        elif event.matched_scar:
            counts["scar_reopen_attempt"] += 1
        elif event.decision == "deny" and event.scar_created:
            counts["unverified_privilege_request"] += 1
        elif event.decision == "approval_required":
            counts["needs_human_approval"] += 1
    if not counts:
        return "insufficient_data", 0
    mode, n = counts.most_common(1)[0]
    return mode, n


def coach_from_session(events: list[SessionEvent] | None = None) -> dict[str, Any]:
    rows = list(events if events is not None else _SESSION)
    fail_mode, fail_count = _dominant_fail_mode(rows)
    god_breaches = sum(1 for e in rows if e.mode == "god" and e.executed and e.tool != "restart_service")
    jail_denies = sum(1 for e in rows if e.mode == "jail" and e.decision == "deny")
    scar_hits = sum(1 for e in rows if e.matched_scar)
    executed = sum(1 for e in rows if e.executed)
    jail_allows = sum(1 for e in rows if e.mode == "jail" and e.decision == "allow" and e.executed)

    recommendations: list[str] = []
    if god_breaches:
        recommendations.append(
            "Keep privileged tools behind the Jail gate — God mode executed IAM mutation with no policy check."
        )
    if fail_mode == "unverified_privilege_request":
        recommendations.append(
            "Promote the unverified-source privilege scar to a standing deny rule for create_service_identity."
        )
    if scar_hits:
        recommendations.append(
            "Scar retrieval worked on replay — log scar_id on every deny so reopen attempts can be trended."
        )
    if not rows:
        recommendations.append("Run Act 1 → 2 → 3 first so Ask ARIA has gate traces to analyze.")
    if not recommendations:
        recommendations.append("Expand the eval set with rotate_secrets and change_network_access attack variants.")

    lesson = [
        {
            "title": "What AgentJail is",
            "body": "A runtime firewall in front of agent tools. It checks who asked, how trusted the source is, and whether this attack was seen before.",
        },
        {
            "title": "What just happened in this session",
            "body": (
                f"God breaches={god_breaches}. Jail denies={jail_denies}. "
                f"Scar intercepts={scar_hits}. Tools that executed={executed}."
            ),
        },
        {
            "title": "Dominant failure mode",
            "body": _FAIL_LABELS.get(fail_mode, fail_mode),
        },
        {
            "title": "Why ARIA is in this demo",
            "body": (
                "Decisions are logged to Weave. Ask ARIA (here via your W&B API key) reads that session, "
                "compares God vs Jail, and proposes the next scar/policy — closing the research loop."
            ),
        },
    ]

    timeline = []
    for e in rows[-8:]:
        if e.mode == "god" and e.executed:
            plain = f"WITHOUT Jail: {e.tool} EXECUTED with no provenance check (dangerous if privileged)."
        elif e.matched_scar:
            plain = f"WITH Jail: {e.tool} BLOCKED by scar memory (attack pattern recognized)."
        elif e.decision == "deny":
            plain = f"WITH Jail: {e.tool} BLOCKED and a new scar was written."
        elif e.decision == "approval_required":
            plain = f"WITH Jail: {e.tool} paused — human must approve."
        elif e.decision == "allow":
            plain = f"WITH Jail: {e.tool} ALLOWED (verified low blast-radius)."
        else:
            plain = e.reason
        timeline.append(
            {
                "at": e.at,
                "mode": e.mode,
                "decision": e.decision,
                "tool": e.tool,
                "plain_english": plain,
                "reason": e.reason,
            }
        )

    aria_prompt = (
        "In the Agent Jail Weave project (rshah88-arizona-state-university/agent-jail), "
        "analyze recent agent_jail.incident traces. Compare God (ungated) vs Jail (gated): "
        "breach rate, deny rate, scar_match rate. Name the dominant failure mode in plain English "
        "and recommend the next policy or scar. Create a short report panel for judges."
    )

    insight = {
        "coach": "Ask ARIA",
        "status": "ready" if rows else "waiting_for_traces",
        "api_key_ready": api_key_ready(),
        "weave_enabled": weave_enabled(),
        "weave_project": weave_project(),
        "weave_url": weave_project_url(),
        "ask_aria_url": weave_project_url(),
        "dominant_fail_mode": fail_mode,
        "dominant_fail_mode_label": _FAIL_LABELS.get(fail_mode, fail_mode),
        "fail_mode_count": fail_count,
        "session": {
            "events": len(rows),
            "god_breaches": god_breaches,
            "jail_denies": jail_denies,
            "jail_allows": jail_allows,
            "scar_hits": scar_hits,
            "executed": executed,
        },
        "summary": _summary_text(fail_mode, god_breaches, jail_denies, scar_hits, rows),
        "lesson": lesson,
        "timeline": timeline,
        "recommendations": recommendations,
        "ask_aria_prompt": aria_prompt,
        "how_to_use_aria": [
            "1. Run Act 1 → 2 → 3 so this session + Weave have nested incident traces.",
            "2. Click Ask ARIA — analysis runs here with your WANDB_API_KEY via W&B Inference.",
            "3. Optional: open Weave to inspect the same traces in the W&B UI.",
        ],
        "aria_report": _fallback_report(
            fail_mode, god_breaches, jail_denies, jail_allows, scar_hits, recommendations, rows
        ),
        "events": [asdict(e) for e in rows[-12:]],
        "llm_enriched": False,
    }
    return insight


def _summary_text(
    fail_mode: str,
    god_breaches: int,
    jail_denies: int,
    scar_hits: int,
    rows: list[SessionEvent],
) -> str:
    if not rows:
        return "No gate events yet. Run the 3-step demo so Ask ARIA has something to read."
    return (
        f"Dominant fail mode: {fail_mode}. "
        f"God breaches={god_breaches}, Jail denies={jail_denies}, scar intercepts={scar_hits}."
    )


def _fallback_report(
    fail_mode: str,
    god_breaches: int,
    jail_denies: int,
    jail_allows: int,
    scar_hits: int,
    recommendations: list[str],
    rows: list[SessionEvent],
) -> dict[str, Any]:
    if not rows:
        return {
            "headline": "Waiting for demo traces",
            "analysis": "Run Act 1 → 2 → 3, then Ask ARIA again.",
            "god_vs_jail": "No events yet.",
            "next_policy": "Play the three acts so scar memory has something to learn.",
            "judge_takeaway": "AgentJail = provenance gate + scar memory; ARIA explains the loop.",
        }
    return {
        "headline": _FAIL_LABELS.get(fail_mode, fail_mode),
        "analysis": (
            f"Session shows {god_breaches} ungated breach(es), {jail_denies} Jail deny(ies), "
            f"and {scar_hits} scar hit(s). Jail still allowed {jail_allows} low-blast-radius action(s)."
        ),
        "god_vs_jail": (
            "God executes privileged tools with no provenance check. "
            "Jail denies unverified privilege, writes scars, and blocks mutated replays while allowing signed safe restarts."
        ),
        "next_policy": recommendations[0] if recommendations else "Keep expanding adversarial eval coverage.",
        "judge_takeaway": (
            "The product is not a blanket blocklist — it is provenance-aware authorization plus persistent attack memory."
        ),
    }


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _message_text(message: Any) -> str:
    if message is None:
        return ""
    for attr in ("content", "reasoning", "refusal"):
        value = getattr(message, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if isinstance(message, dict):
        for key in ("content", "reasoning", "refusal"):
            value = message.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def maybe_llm_enrich(insight: dict[str, Any]) -> dict[str, Any]:
    """Ask ARIA in-app via W&B Inference using WANDB_API_KEY."""
    key = os.getenv("WANDB_API_KEY")
    if not key:
        insight["llm_enriched"] = False
        insight["aria_status"] = "missing_api_key"
        return insight
    if not insight.get("session", {}).get("events"):
        insight["llm_enriched"] = False
        insight["aria_status"] = "waiting_for_traces"
        return insight

    try:
        from openai import OpenAI

        client = OpenAI(
            base_url="https://api.inference.wandb.ai/v1",
            api_key=key,
            project=os.getenv("WEAVE_PROJECT") or weave_project(),
        )
        payload = {
            "project": insight.get("weave_project"),
            "fail_mode": insight.get("dominant_fail_mode"),
            "session": insight.get("session"),
            "timeline": insight.get("timeline"),
            "recommendations": insight.get("recommendations"),
            "events": insight.get("events"),
        }
        response = client.chat.completions.create(
            model=os.getenv("ARIA_COACH_MODEL", "zai-org/GLM-5.3-Flash"),
            temperature=0.2,
            max_tokens=1200,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Ask ARIA for Agent Jail (runtime firewall: provenance + scar memory). "
                        "Return ONE compact JSON object and nothing else. Required string keys: "
                        "headline, summary, analysis, god_vs_jail, next_policy, judge_takeaway. "
                        "Also include recommendations as a JSON array of 2-3 short strings. "
                        "Each string field must be 1-2 sentences. No markdown."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Compare God vs Jail for judges from this session JSON. "
                        f"{json.dumps(payload, default=str)}"
                    ),
                },
            ],
        )
        message = response.choices[0].message if response.choices else None
        text = _message_text(message)
        # Prefer a trailing JSON object if the model reasoned first.
        parsed = _extract_json(text) if text else None
        if parsed:
            report = {
                "headline": str(parsed.get("headline") or insight["dominant_fail_mode_label"])[:200],
                "analysis": str(parsed.get("analysis") or parsed.get("summary") or "")[:900],
                "god_vs_jail": str(parsed.get("god_vs_jail") or "")[:700],
                "next_policy": str(parsed.get("next_policy") or "")[:400],
                "judge_takeaway": str(parsed.get("judge_takeaway") or "")[:400],
            }
            insight["aria_report"] = report
            summary = str(parsed.get("summary") or report["analysis"]).strip()
            if summary:
                insight["summary"] = summary[:900]
            recs = parsed.get("recommendations")
            if isinstance(recs, list) and recs:
                insight["recommendations"] = [str(r)[:240] for r in recs[:4]]
            insight["llm_enriched"] = True
            insight["aria_status"] = "live"
            return insight
        if text:
            insight["summary"] = text[:900]
            insight["aria_report"] = {
                **(insight.get("aria_report") or {}),
                "analysis": text[:900],
            }
            insight["llm_enriched"] = True
            insight["aria_status"] = "live_raw"
            return insight
        insight["llm_enriched"] = False
        insight["aria_status"] = "empty_model_response"
        return insight
    except Exception as exc:
        insight["aria_status"] = f"inference_error:{type(exc).__name__}:{exc}"[:180]
        insight["llm_enriched"] = False
        return insight
