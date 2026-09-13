"""W&B Weave instrumentation with nested parent/child traces for ARIA."""

from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

_enabled = False
_PROJECT = os.getenv("WEAVE_PROJECT", "rshah88-arizona-state-university/agent-jail")

try:
    import weave

    if os.getenv("WANDB_API_KEY"):
        try:
            weave.init(_PROJECT)
            _enabled = True
        except Exception:
            _enabled = False

    @weave.op(name="agent_jail.guard_decision")
    def guard_decision_op(
        tool_call: dict[str, Any],
        result: dict[str, Any],
        scenario: str = "",
        mode: str = "jail",
    ) -> dict[str, Any]:
        return {
            "scenario": scenario,
            "mode": mode,
            "tool_call": tool_call,
            "result": result,
            "scores": _scores(tool_call, result, mode),
        }

    @weave.op(name="agent_jail.incident")
    def incident_op(
        scenario: str,
        mode: str,
        tool_call: dict[str, Any],
        result: dict[str, Any],
        attack_variant: str | None = None,
    ) -> dict[str, Any]:
        """Parent trace — child guard_decision nests underneath for ARIA."""
        nested = guard_decision_op(tool_call, result, scenario=scenario, mode=mode)
        return {
            "scenario": scenario,
            "mode": mode,
            "attack_variant": attack_variant,
            "decision": nested,
        }

except ImportError:

    def guard_decision_op(
        tool_call: dict[str, Any],
        result: dict[str, Any],
        scenario: str = "",
        mode: str = "jail",
    ) -> dict[str, Any]:
        return {
            "scenario": scenario,
            "mode": mode,
            "tool_call": tool_call,
            "result": result,
            "scores": _scores(tool_call, result, mode),
        }

    def incident_op(
        scenario: str,
        mode: str,
        tool_call: dict[str, Any],
        result: dict[str, Any],
        attack_variant: str | None = None,
    ) -> dict[str, Any]:
        nested = guard_decision_op(tool_call, result, scenario=scenario, mode=mode)
        return {
            "scenario": scenario,
            "mode": mode,
            "attack_variant": attack_variant,
            "decision": nested,
        }


def _scores(tool_call: dict[str, Any], result: dict[str, Any], mode: str) -> dict[str, float]:
    return {
        "executed": 1.0 if result.get("executed") else 0.0,
        "denied": 1.0 if result.get("decision") == "deny" else 0.0,
        "scar_match": 1.0 if result.get("matched_scar") else 0.0,
        "god_breach": 1.0
        if mode == "god" and result.get("executed") and tool_call.get("tool") != "restart_service"
        else 0.0,
    }


def _serialize_result(result: Any) -> dict[str, Any]:
    outcome = asdict(result) if hasattr(result, "__dataclass_fields__") else dict(result)
    scar = outcome.get("scar_created")
    if scar is not None and hasattr(scar, "__dataclass_fields__"):
        outcome = {**outcome, "scar_created": asdict(scar)}
    return outcome


def record_decision(
    tool_call: Any,
    result: Any,
    *,
    scenario: str = "",
    mode: str = "jail",
    attack_variant: str | None = None,
) -> None:
    """Log one nested incident tree. Never affects gate outcomes."""
    if not _enabled:
        return
    try:
        payload = asdict(tool_call) if hasattr(tool_call, "__dataclass_fields__") else dict(tool_call)
        outcome = _serialize_result(result)
        attrs = {
            "agent_jail.scenario": scenario,
            "agent_jail.mode": mode,
            "agent_jail.tool": payload.get("tool"),
        }
        if _enabled:
            import weave as _weave

            with _weave.attributes(attrs):
                incident_op(
                    scenario=scenario,
                    mode=mode,
                    tool_call=payload,
                    result=outcome,
                    attack_variant=attack_variant,
                )
        else:
            incident_op(
                scenario=scenario,
                mode=mode,
                tool_call=payload,
                result=outcome,
                attack_variant=attack_variant,
            )
    except Exception:
        return


def finalize_evaluation(summary: dict[str, Any] | None = None) -> None:
    if not _enabled:
        return
    try:
        import weave as _weave

        @_weave.op(name="agent_jail.coach_summary")
        def coach_summary(payload: dict[str, Any]) -> dict[str, Any]:
            return payload

        coach_summary(summary or {})
    except Exception:
        return


def weave_enabled() -> bool:
    return _enabled


def weave_project() -> str:
    return os.getenv("WEAVE_PROJECT", _PROJECT)
