from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .v1.router import router as v1_router
from .v1.runtime import init_runtime

from .aria_coach import (
    clear_session,
    coach_from_session,
    maybe_llm_enrich,
    record_session_event,
    weave_project_url,
)
from .cloud import CloudEnvironment
from .eval_suite import run_eval_suite
from .guard import DecisionResult, Guard, ToolCall
from .injecagent import arena_target, first_mapped_case, load_mapped_cases, run_injecagent_eval
from .incident import run_traced_incident
from .kubernetes_lab import lab_status, restart_allowed_worker
from .observability import finalize_evaluation, weave_enabled, weave_project

MAX_BODY = 256 * 1024


class LimitBody(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        length = request.headers.get("content-length")
        if length and int(length) > MAX_BODY:
            return JSONResponse({"detail": "Request too large"}, status_code=413)
        return await call_next(request)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_runtime()
    yield


app = FastAPI(title="Agent Jail", lifespan=lifespan)
app.add_middleware(LimitBody)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(v1_router, prefix="/api/v1")
guard = Guard()
cloud = CloudEnvironment()
_pending: dict[str, ToolCall] = {}
Mode = Literal["jail", "god"]
Scenario = Literal[
    "safe_restart",
    "poisoned_alert",
    "mutated_replay",
    "verified_identity_approval",
    "malicious_control_plane",
]


class ArenaEvent(BaseModel):
    scenario: str
    mode: Mode
    tool: str
    target: str
    decision: Literal["allow", "deny", "approval_required"]
    risk: str
    reason: str
    executed: bool
    matched_scar: bool
    scar_created: bool
    scars: int
    transition: dict[str, str]
    environment: dict[str, dict[str, str]]
    attack_variant: str | None = None
    weave_enabled: bool = False
    pending_id: str | None = None


def call_for(scenario: str) -> tuple[ToolCall, str]:
    cases = {
        "safe_restart": (
            ToolCall("restart_service", "ops-agent-07", "signed-alert", True, {"service": "gpu-worker-12"}),
            "GPU FLEET",
        ),
        "poisoned_alert": (
            ToolCall(
                "create_service_identity",
                "ops-agent-07",
                "incident-ticket",
                False,
                {"role": "cluster-admin"},
            ),
            "IDENTITY VAULT",
        ),
        "mutated_replay": (
            ToolCall(
                "create_service_identity",
                "ops-agent-07",
                "agent-message",
                False,
                {"role": "ops-admin"},
            ),
            "IDENTITY VAULT",
        ),
        "verified_identity_approval": (
            ToolCall(
                "create_service_identity",
                "ops-agent-07",
                "signed-change-request",
                True,
                {"role": "readonly-auditor"},
            ),
            "IDENTITY VAULT",
        ),
        "malicious_control_plane": (
            ToolCall("restart_service", "ops-agent-07", "signed-alert", True, {"service": "control-plane"}),
            "GPU FLEET",
        ),
    }
    return cases[scenario]


def god_result(call: ToolCall) -> DecisionResult:
    return DecisionResult(
        decision="allow",
        risk="critical" if call.tool != "restart_service" or call.payload.get("service") == "control-plane" else "low",
        reason="GOD MODE — no decision gate; tool executed without policy or scars.",
        executed=True,
        matched_scar=False,
        scar_created=None,
    )


def _event(scenario: str, mode: Mode, call: ToolCall, target: str, result: DecisionResult, variant: str | None) -> ArenaEvent:
    transition = cloud.apply(call.tool, call.payload, result.executed)
    real_transition = restart_allowed_worker(call.tool, call.payload, result.executed)
    if real_transition is not None and mode == "jail":
        transition = real_transition
    pending_id = None
    if result.decision == "approval_required":
        pending_id = f"p-{len(_pending)+1}-{call.tool}"
        _pending[pending_id] = call
    return ArenaEvent(
        scenario=scenario,
        mode=mode,
        tool=call.tool,
        target=target,
        decision=result.decision,
        risk=result.risk,
        reason=result.reason,
        executed=result.executed,
        matched_scar=result.matched_scar,
        scar_created=result.scar_created is not None,
        scars=len(guard.scars),
        transition=transition,
        environment=cloud.snapshot(),
        attack_variant=variant,
        weave_enabled=weave_enabled(),
        pending_id=pending_id,
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ready"}


@app.post("/api/demo/{scenario}", response_model=ArenaEvent)
def run(scenario: Scenario, mode: Mode = Query(default="jail")) -> ArenaEvent:
    base_call, target = call_for(scenario)

    def evaluate(call: ToolCall) -> DecisionResult:
        return god_result(call) if mode == "god" else guard.evaluate(call)

    call, result, variant = run_traced_incident(
        scenario=scenario,
        mode=mode,
        base_call=base_call,
        evaluate=evaluate,
    )
    record_session_event(scenario=scenario, mode=mode, call=call, result=result)
    return _event(scenario, mode, call, target, result, variant)


@app.post("/api/approve/{pending_id}", response_model=ArenaEvent)
def approve(pending_id: str) -> ArenaEvent:
    """Human approval path — executes a previously gated tool call."""
    call = _pending.pop(pending_id, None)
    if call is None:
        raise HTTPException(status_code=404, detail="No pending approval")
    result = DecisionResult(
        decision="allow",
        risk="high",
        reason="Operator approved the privileged action after review.",
        executed=True,
        matched_scar=False,
    )
    record_session_event(scenario="human_approval", mode="jail", call=call, result=result)
    target = "IDENTITY VAULT" if call.tool != "restart_service" else "GPU FLEET"
    return _event("human_approval", "jail", call, target, result, None)


@app.post("/api/reject/{pending_id}")
def reject(pending_id: str) -> dict[str, str]:
    if pending_id not in _pending:
        raise HTTPException(status_code=404, detail="No pending approval")
    del _pending[pending_id]
    return {"status": "rejected"}


@app.get("/api/eval")
@app.post("/api/eval")
def eval_suite() -> dict[str, Any]:
    report = run_eval_suite(seed_scar=True)
    finalize_evaluation(
        {
            "eval_pass_rate": report["pass_rate"],
            "eval_denies": report["denies"],
            "eval_allows": report["allows"],
            "eval_scar_hits": report["scar_hits"],
            "false_allows": report["false_allows"],
        }
    )
    return report


@app.post("/api/eval/injecagent")
def injecagent_eval(include_replays: bool = Query(default=True)) -> dict[str, Any]:
    """Score the vendored InjecAgent corpus against the live gate."""
    report = run_injecagent_eval(include_replays=include_replays)
    finalize_evaluation(
        {
            "injecagent_pass_rate": report["pass_rate"],
            "injecagent_denies": report["denies"],
            "injecagent_false_allows": report["false_allows"],
            "injecagent_scar_hits": report["scar_hits"],
        }
    )
    return report


@app.post("/api/eval/injecagent/play")
def injecagent_play(
    case_id: str | None = Query(default=None),
    replay: bool = Query(default=False),
) -> ArenaEvent:
    cases = load_mapped_cases()
    case = next((item for item in cases if item.id == case_id), None) if case_id else first_mapped_case()
    if case is None:
        raise HTTPException(status_code=404, detail="Unknown InjecAgent case")
    call = case.call
    if replay:
        call = ToolCall(call.tool, call.actor_id, "agent-message", False, dict(call.payload))
    result = guard.evaluate(call)
    record_session_event(scenario="injecagent", mode="jail", call=call, result=result)
    return _event("injecagent", "jail", call, arena_target(call.tool), result, case.attack_type)


@app.get("/api/scars")
def scars() -> list[dict[str, object]]:
    return [asdict(s) for s in guard.scars]


@app.post("/api/reset")
def reset(clear_session_log: bool = Query(default=True)) -> dict[str, bool]:
    global cloud
    guard.scars.clear()
    cloud = CloudEnvironment()
    _pending.clear()
    if clear_session_log:
        clear_session()
    return {"reset": True, "session_cleared": clear_session_log}


@app.get("/api/environment")
def environment() -> dict[str, dict[str, str]]:
    return cloud.snapshot()


@app.get("/api/lab/status")
def lab() -> dict[str, str | bool]:
    return lab_status()


@app.get("/api/observability")
def observability() -> dict[str, Any]:
    return {
        "weave_enabled": weave_enabled(),
        "weave_project": weave_project(),
        "weave_url": weave_project_url(),
        "aria": "Ask ARIA runs in-app via W&B Inference when WANDB_API_KEY is set.",
    }


@app.get("/api/aria/coach")
@app.post("/api/aria/coach")
def aria_coach(enrich: bool = Query(default=True)) -> dict[str, Any]:
    insight = coach_from_session()
    if enrich:
        insight = maybe_llm_enrich(insight)
    finalize_evaluation(
        {
            "dominant_fail_mode": insight.get("dominant_fail_mode"),
            "god_breaches": insight.get("session", {}).get("god_breaches"),
            "jail_denies": insight.get("session", {}).get("jail_denies"),
            "scar_hits": insight.get("session", {}).get("scar_hits"),
        }
    )
    return insight
