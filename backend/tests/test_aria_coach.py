import unittest

from app.aria_coach import clear_session, coach_from_session, record_session_event
from app.guard import DecisionResult, ToolCall


class AriaCoachTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_session()

    def tearDown(self) -> None:
        clear_session()

    def test_coach_reports_god_breach_and_scar_hit(self) -> None:
        record_session_event(
            scenario="poisoned_alert",
            mode="god",
            call=ToolCall("create_service_identity", "ops-agent-07", "incident-ticket", False, {"role": "cluster-admin"}),
            result=DecisionResult("allow", "critical", "god", True, False, None),
        )
        record_session_event(
            scenario="poisoned_alert",
            mode="jail",
            call=ToolCall("create_service_identity", "ops-agent-07", "incident-ticket", False, {"role": "cluster-admin"}),
            result=DecisionResult("deny", "critical", "deny", False, False, None),
        )
        record_session_event(
            scenario="mutated_replay",
            mode="jail",
            call=ToolCall("create_service_identity", "ops-agent-07", "agent-message", False, {"role": "ops-admin"}),
            result=DecisionResult("deny", "critical", "scar", False, True, None),
        )

        insight = coach_from_session()
        self.assertEqual(insight["session"]["god_breaches"], 1)
        self.assertEqual(insight["session"]["scar_hits"], 1)
        self.assertIn("ask_aria_prompt", insight)
        self.assertTrue(insight["weave_url"].startswith("https://wandb.ai/"))

    def test_empty_session_is_safe(self) -> None:
        insight = coach_from_session([])
        self.assertEqual(insight["dominant_fail_mode"], "insufficient_data")
        self.assertEqual(insight["session"]["events"], 0)


if __name__ == "__main__":
    unittest.main()
