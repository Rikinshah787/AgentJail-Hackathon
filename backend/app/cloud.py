from dataclasses import dataclass, field

@dataclass
class CloudEnvironment:
    workloads: dict[str, str] = field(default_factory=lambda: {"gpu-worker-12": "degraded", "gpu-worker-09": "healthy", "control-plane": "healthy"})
    identities: dict[str, str] = field(default_factory=lambda: {"ops-agent-07": "workload-operator"})
    secrets: dict[str, str] = field(default_factory=lambda: {"training-registry": "sealed"})
    network: dict[str, str] = field(default_factory=lambda: {"debug-egress": "closed"})

    def apply(self, tool: str, payload: dict[str, str], allowed: bool) -> dict[str, str]:
        if not allowed:
            return {"status": "blocked", "summary": f"{tool} was stopped before cloud mutation", "next_actions": "review scar or request approval"}
        if tool == "restart_service":
            service = payload.get("service", "gpu-worker-12")
            self.workloads[service] = "recovering"
            return {"status": "applied", "summary": f"{service} entered recovery", "next_actions": "observe workload health"}
        if tool == "create_service_identity":
            self.identities["temporary-ops-admin"] = payload.get("role", "unknown")
            return {"status": "applied", "summary": "identity created", "next_actions": "require human review"}
        return {"status": "approval_required", "summary": "no mutation applied", "next_actions": "operator approval required"}

    def snapshot(self) -> dict[str, dict[str, str]]:
        return {"workloads": self.workloads, "identities": self.identities, "secrets": self.secrets, "network": self.network}
