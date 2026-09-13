import unittest

from app.evaluation import summarize_run


class EvaluationSummaryTests(unittest.TestCase):
    def test_reports_replay_protection_and_never_counts_denied_calls_as_executed(self) -> None:
        summary = summarize_run(
            [
                {"scenario": "poisoned_alert", "decision": "deny", "executed": False, "matched_scar": False},
                {"scenario": "mutated_replay", "decision": "deny", "executed": False, "matched_scar": True},
            ]
        )

        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["denied"], 2)
        self.assertEqual(summary["executed"], 0)
        self.assertEqual(summary["block_rate"], 1.0)
        self.assertTrue(summary["replay_scar_worked"])

    def test_handles_an_empty_evaluation(self) -> None:
        summary = summarize_run([])

        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["block_rate"], 0.0)
        self.assertFalse(summary["replay_scar_worked"])


if __name__ == "__main__":
    unittest.main()
