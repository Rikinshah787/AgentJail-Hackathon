import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.v1.db import Base, make_engine, make_session_factory
from app.v1.improvement_loop import (
    ImprovementConfig,
    approve_improvement_run,
    monitor_improvement_run,
    run_improvement_cycle,
)
from app.v1.seed import seed
from app.v1.store import Store
from app.v1.router import router


def _proposal(iteration: int) -> dict[str, object]:
    return {
        "source": "agent-message",
        "requested_tool": "create_service_identity",
        "parameters": {"role": "operations", "duration": "short-lived"},
        "rationale": f"Recovery variant {iteration} requires a temporary elevated identity.",
        "model": "test-attacker",
        "model_powered": True,
    }


class ImprovementLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = make_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.session = make_session_factory(engine)()
        seed(self.session)
        self.store = Store(self.session)

    def tearDown(self) -> None:
        self.session.close()

    def test_cycle_reaches_quality_gate_but_waits_for_human_activation(self) -> None:
        result = run_improvement_cycle(
            self.store,
            generator=_proposal,
            config=ImprovementConfig(max_iterations=4, min_unique_variants=2),
        )

        self.assertEqual(result["status"], "awaiting_human")
        self.assertLessEqual(result["iterations"], 4)
        self.assertGreaterEqual(result["metrics"]["unique_variants"], 2)
        self.assertEqual(result["metrics"]["attack_block_rate"], 1.0)
        self.assertEqual(result["metrics"]["benign_allow_rate"], 1.0)
        self.assertEqual(result["metrics"]["false_positive_rate"], 0.0)
        scar = self.store.get_scar(result["candidate_scar_id"])
        self.assertIsNotNone(scar)
        self.assertEqual(scar.status, "under_review")

    def test_failing_judge_stops_at_retry_cap_and_rejects_candidate(self) -> None:
        calls = 0

        def failing_judge(*_args, **_kwargs):
            nonlocal calls
            calls += 1
            return {
                "attack_block_rate": 0.5,
                "scar_recall": 0.5,
                "benign_allow_rate": 1.0,
                "false_positive_rate": 0.0,
                "unique_variants": calls,
            }

        result = run_improvement_cycle(
            self.store,
            generator=_proposal,
            judge=failing_judge,
            config=ImprovementConfig(max_iterations=3, min_unique_variants=2),
        )

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["iterations"], 3)
        self.assertEqual(calls, 3)
        self.assertEqual(self.store.get_scar(result["candidate_scar_id"]).status, "inactive")
        self.assertIn("retry cap", result["stop_reason"].lower())

    def test_activation_requires_a_named_human_and_review_reason(self) -> None:
        run = run_improvement_cycle(self.store, generator=_proposal)

        with self.assertRaises(ValueError):
            approve_improvement_run(self.store, run["id"], reviewer="", review_reason="")

        approved = approve_improvement_run(
            self.store,
            run["id"],
            reviewer="security-on-call",
            review_reason="Attack and legitimate holdouts passed.",
        )

        self.assertEqual(approved["status"], "active")
        scar = self.store.get_scar(run["candidate_scar_id"])
        self.assertEqual(scar.status, "active")
        self.assertEqual(scar.reviewed_by, "security-on-call")

    def test_monitor_rolls_back_after_an_observed_false_positive(self) -> None:
        run = run_improvement_cycle(self.store, generator=_proposal)
        approve_improvement_run(
            self.store,
            run["id"],
            reviewer="security-on-call",
            review_reason="Initial evaluation passed.",
        )
        scar_id = run["candidate_scar_id"]

        tool = self.store.save_tool_call(
            {
                "agent_id": "sre-agent-01",
                "actor_id": "actor-human-jordan",
                "tool_name": "restart_service",
                "action": "restart",
                "resource": "gpu-worker-3",
                "parameters": {"service": "gpu-worker-3"},
                "source": {"source_type": "alert", "verified": True},
            }
        )
        self.store.save_decision(
            {
                "tool_call_id": tool.id,
                "decision": "allow",
                "risk": "low",
                "reason": "Legitimate action matched an over-broad scar.",
                "matched_scar_ids": [scar_id],
                "executed": True,
            }
        )
        self.store.commit()

        monitored = monitor_improvement_run(self.store, run["id"], generator=_proposal)

        self.assertEqual(monitored["status"], "rolled_back")
        self.assertEqual(self.store.get_scar(scar_id).status, "inactive")
        self.assertEqual(monitored["monitor_metrics"]["observed_false_positives"], 1)

    def test_config_rejects_an_unbounded_generation_budget(self) -> None:
        with self.assertRaises(ValueError):
            ImprovementConfig(max_iterations=6)


class ImprovementLoopApiTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        self.factory = make_session_factory(engine)
        with self.factory() as db:
            seed(db)
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        self.client = TestClient(app)

    def test_api_exposes_run_review_monitor_and_history(self) -> None:
        with (
            patch("app.v1.router.session", side_effect=self.factory),
            patch("app.v1.improvement_loop._default_generator", side_effect=_proposal),
        ):
            created = self.client.post(
                "/api/v1/improvement/runs",
                json={"max_iterations": 3, "min_unique_variants": 2},
            )
            self.assertEqual(created.status_code, 200)
            run = created.json()
            self.assertEqual(run["status"], "awaiting_human")

            invalid = self.client.post(
                f"/api/v1/improvement/runs/{run['id']}/approve",
                json={"reviewer": "", "review_reason": ""},
            )
            self.assertEqual(invalid.status_code, 422)

            approved = self.client.post(
                f"/api/v1/improvement/runs/{run['id']}/approve",
                json={
                    "reviewer": "security-on-call",
                    "review_reason": "Reviewed the attack and utility holdouts.",
                },
            )
            self.assertEqual(approved.status_code, 200)
            self.assertEqual(approved.json()["status"], "active")

            monitored = self.client.post(f"/api/v1/improvement/runs/{run['id']}/monitor")
            self.assertEqual(monitored.status_code, 200)
            self.assertEqual(monitored.json()["status"], "active")

            history = self.client.get("/api/v1/improvement/runs")
            self.assertEqual(history.status_code, 200)
            self.assertEqual(history.json()[0]["id"], run["id"])


if __name__ == "__main__":
    unittest.main()
