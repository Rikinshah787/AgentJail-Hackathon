"""Pure, notebook-friendly summaries for Agent Jail evaluation runs."""

from typing import Iterable, Mapping


def summarize_run(events: Iterable[Mapping[str, object]]) -> dict[str, int | float | bool]:
    """Return judge-facing safety metrics without retaining event payloads."""
    rows = list(events)
    total = len(rows)
    denied = sum(row.get("decision") == "deny" for row in rows)
    executed = sum(bool(row.get("executed")) for row in rows)
    replay_scar_worked = any(
        row.get("scenario") == "mutated_replay" and bool(row.get("matched_scar"))
        for row in rows
    )
    return {
        "total": total,
        "denied": denied,
        "executed": executed,
        "block_rate": denied / total if total else 0.0,
        "replay_scar_worked": replay_scar_worked,
    }
