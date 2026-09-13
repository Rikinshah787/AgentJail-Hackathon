"""Traced incident turn: nests mutate_alert + guard_decision under one parent."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Literal

from .attacker import generate_attack_proposal
from .guard import DecisionResult, ToolCall
from .observability import weave_enabled

Mode = Literal["jail", "god"]


def _serialize_result(result: DecisionResult) -> dict[str, Any]:
    outcome = asdict(result)
    scar = outcome.get("scar_created")
    if scar is not None and not isinstance(scar, dict):
        outcome = {**outcome, "scar_created": asdict(scar)}
    return outcome


def run_traced_incident(
    *,
    scenario: str,
    mode: Mode,
    base_call: ToolCall,
    evaluate: Callable[[ToolCall], DecisionResult],
) -> tuple[ToolCall, DecisionResult, str | None, dict[str, object] | None]:
    """
    Returns (call, result, attack_variant).

    When Weave is on, one parent `agent_jail.incident` contains:
    - agent_jail.mutate_alert (+ nested OpenAI) when scenario needs mutation
    - agent_jail.guard_decision
    """

    def _execute() -> tuple[ToolCall, DecisionResult, str | None, dict[str, object] | None]:
        variant: str | None = None
        proposal: dict[str, object] | None = None
        call = base_call
        if scenario == "mutated_replay":
            proposal = generate_attack_proposal()
            variant = str(proposal["rationale"])
            call = ToolCall(
                str(proposal["requested_tool"]),
                base_call.actor_id,
                str(proposal["source"]),
                base_call.source_verified,
                {**base_call.payload, **proposal["parameters"], "alert": variant},
            )
        result = evaluate(call)
        return call, result, variant, proposal

    if not weave_enabled():
        return _execute()

    import weave

    from .observability import guard_decision_op

    # Hold real objects for the API while still emitting a nested Weave tree.
    box: dict[str, Any] = {}

    @weave.op(name="agent_jail.incident")
    def incident() -> dict[str, Any]:
        call, result, variant, proposal = _execute()
        box["call"] = call
        box["result"] = result
        box["variant"] = variant
        box["proposal"] = proposal
        payload = asdict(call)
        outcome = _serialize_result(result)
        decision = guard_decision_op(payload, outcome, scenario=scenario, mode=mode)
        return {
            "scenario": scenario,
            "mode": mode,
            "attack_variant": variant,
            "attacker_proposal": proposal,
            "tool_call": payload,
            "result": outcome,
            "decision": decision,
        }

    with weave.attributes(
        {
            "agent_jail.scenario": scenario,
            "agent_jail.mode": mode,
            "agent_jail.tool": base_call.tool,
        }
    ):
        incident()

    return box["call"], box["result"], box["variant"], box["proposal"]
