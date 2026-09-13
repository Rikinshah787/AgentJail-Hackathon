"""HTTP API for the AgentJail UI at /ariai-logic."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .db import ScarRow, utcnow
from .demo import run_scenario
from .evaluate import run_harness
from .gateway import Gateway
from .probe import run_independent_probes
from .runtime import executor, reset_demo, session
from .schemas import ApprovalActionRequest, AuthorizeRequest, DemoRunRequest
from .serialize import to_plain
from .store import Store, row_to_dict
from .weave_eval import run_weave_evaluation
from .god_vs_jail import run_god_vs_jail
from .tracing import seed_agent_demo_conversation, weave_status as weave_status_payload

router = APIRouter()


@router.post("/authorize")
def authorize(body: AuthorizeRequest):
    with session() as db:
        store = Store(db)
        try:
            result = Gateway(store, executor()).authorize(body)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return to_plain(result)


@router.get("/dashboard/summary")
@router.get("/dashboard")
def dashboard():
    with session() as db:
        return Store(db).dashboard()


@router.get("/incidents")
def incidents():
    with session() as db:
        return Store(db).incidents()


@router.get("/incidents/{incident_id}")
def incident(incident_id: str):
    with session() as db:
        item = Store(db).incident_detail(incident_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Incident not found")
        return item


@router.get("/scars")
def scars():
    with session() as db:
        return Store(db).scars()


@router.post("/scars/{scar_id}/activate")
def activate_scar(scar_id: str):
    with session() as db:
        row = db.get(ScarRow, scar_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Scar not found")
        row.status = "active"
        row.reviewed_by = row.reviewed_by or "demo-reviewer"
        db.commit()
        return row_to_dict(row)


@router.post("/scars/{scar_id}/deactivate")
def deactivate_scar(scar_id: str):
    with session() as db:
        row = db.get(ScarRow, scar_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Scar not found")
        row.status = "inactive"
        db.commit()
        return row_to_dict(row)


@router.get("/approvals")
def approvals():
    with session() as db:
        return Store(db).approvals()


@router.post("/approvals/{approval_id}/approve")
def approve(approval_id: str, body: ApprovalActionRequest):
    if not body.review_reason.strip():
        raise HTTPException(status_code=422, detail="A review reason is required.")
    with session() as db:
        try:
            return Gateway(Store(db), executor()).resolve_approval(
                approval_id,
                approve=True,
                reviewer=body.reviewer,
                review_reason=body.review_reason,
                parameters=body.parameters,
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="Approval not found")
        except PermissionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/approvals/{approval_id}/deny")
def deny(approval_id: str, body: ApprovalActionRequest):
    if not body.review_reason.strip():
        raise HTTPException(status_code=422, detail="A review reason is required.")
    with session() as db:
        try:
            return Gateway(Store(db), executor()).resolve_approval(
                approval_id,
                approve=False,
                reviewer=body.reviewer,
                review_reason=body.review_reason,
                parameters=body.parameters,
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="Approval not found")
        except PermissionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/policies")
def policies():
    with session() as db:
        return Store(db).policies()


@router.get("/evaluations/summary")
@router.get("/evaluations")
def evaluations():
    with session() as db:
        from .tracing import trace_eval_summary

        summary = run_harness(Store(db))
        # Compact payload for Weave (avoid dumping every InjecAgent row).
        trace_eval_summary(
            {
                "containment_rate": summary.get("containment_rate"),
                "benign_utility": summary.get("benign_utility"),
                "false_positive_rate": summary.get("false_positive_rate"),
                "probe_passed": (summary.get("independent_probes") or {}).get("passed"),
                "probe_total": (summary.get("independent_probes") or {}).get("total"),
                "injec_holdout": {
                    "size": (summary.get("injecagent_holdout") or {}).get("holdout_size"),
                    "unprotected_execution_rate": (summary.get("injecagent_holdout") or {}).get(
                        "unprotected_execution_rate"
                    ),
                    "agentjail_execution_rate": (summary.get("injecagent_holdout") or {}).get(
                        "agentjail_execution_rate"
                    ),
                },
                "honest_claims": summary.get("honest_claims") or [],
            }
        )
        return summary


@router.get("/weave/status")
def weave_status():
    return weave_status_payload()


@router.post("/weave/agent-demo")
def weave_agent_demo():
    """Seed a multi-turn SRE Agent conversation into the Weave Agents tab."""
    return seed_agent_demo_conversation()


@router.post("/evaluations/weave-run")
def evaluations_weave_run(include_injec: bool = True):
    """Run a full Weave EvaluationLogger suite (Evals tab + nested authorize traces)."""
    with session() as db:
        return run_weave_evaluation(Store(db), include_injec=include_injec)


@router.post("/evaluations/god-vs-jail")
def evaluations_god_vs_jail():
    """Headline comparison: no_guard vs agentjail vs agentjail+scar on the same attack."""
    with session() as db:
        return run_god_vs_jail(Store(db))


@router.post("/evaluations/probe")
def evaluations_probe():
    """Independent-observer proofs only (ledger + state)."""
    with session() as db:
        return run_independent_probes(Store(db))


@router.post("/demo/run")
def demo_run(body: DemoRunRequest):
    with session() as db:
        result = run_scenario(Store(db), body.scenario, executor())
        if result.get("status") == "failed":
            return JSONResponse(result, status_code=500)
        return result


@router.post("/demo/reset")
def demo_reset():
    reset_demo()
    return {"reset": True, "at": utcnow().isoformat()}
