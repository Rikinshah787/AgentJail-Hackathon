import unittest

from app.v1.db import Base, make_engine, make_session_factory
from app.v1.improvement_loop import (
    ImprovementConfig,
    approve_improvement_run,
    monitor_improvement_run,
    run_improvement_cycle,
)
from app.v1.seed import seed
from app.v1.store import Store


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


if __name__ == "__main__":
    unittest.main()
