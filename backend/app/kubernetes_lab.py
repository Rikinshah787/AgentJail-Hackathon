"""Narrow real-cluster adapter for the isolated Agent Jail lab only."""

import os
import subprocess

NAMESPACE = "agent-jail-lab"
DEPLOYMENT = "gpu-worker-12"


def lab_status() -> dict[str, str | bool]:
    """Read-only evidence of the isolated lab and its narrow mutation boundary."""
    if not os.getenv("AGENT_JAIL_REAL_LAB"):
        return {
            "connected": False,
            "mode": "simulation",
            "cluster": "not-connected",
            "namespace": NAMESPACE,
            "workload": DEPLOYMENT,
            "workload_ready": "not-queried",
            "mutation_scope": "none",
        }
    try:
        result = subprocess.run(
            [
                "kubectl",
                "get",
                f"deployment/{DEPLOYMENT}",
                "-n",
                NAMESPACE,
                "-o",
                "jsonpath={.status.readyReplicas}/{.spec.replicas}",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=8,
        )
        return {
            "connected": True,
            "mode": "isolated_kubernetes",
            "cluster": "kind-agent-jail-lab",
            "namespace": NAMESPACE,
            "workload": DEPLOYMENT,
            "workload_ready": result.stdout.strip() or "unknown",
            "mutation_scope": "restart deployment/gpu-worker-12 only",
        }
    except (subprocess.SubprocessError, OSError):
        return {
            "connected": False,
            "mode": "lab_unavailable",
            "cluster": "kind-agent-jail-lab",
            "namespace": NAMESPACE,
            "workload": DEPLOYMENT,
            "workload_ready": "unavailable",
            "mutation_scope": "restart deployment/gpu-worker-12 only",
        }


def restart_allowed_worker(tool: str, payload: dict[str, str], allowed: bool) -> dict[str, str] | None:
    if not os.getenv("AGENT_JAIL_REAL_LAB"):
        return None
    if not allowed or tool != "restart_service" or payload.get("service") != DEPLOYMENT:
        return {"status": "blocked", "summary": "No real Kubernetes mutation authorized", "next_actions": "use the guarded restart tool only"}
    try:
        subprocess.run(["kubectl", "rollout", "restart", f"deployment/{DEPLOYMENT}", "-n", NAMESPACE], check=True, capture_output=True, text=True, timeout=20)
        return {"status": "applied", "summary": "Real Kubernetes rollout restart triggered", "next_actions": "observe pod replacement"}
    except (subprocess.SubprocessError, OSError):
        return {"status": "error", "summary": "Kubernetes restart failed without changing authorization", "next_actions": "inspect local cluster health"}
