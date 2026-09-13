import unittest

from fastapi.testclient import TestClient

from app.injecagent import load_mapped_cases, map_attacker_tool, run_injecagent_eval, source_for
from app.main import app


class InjecAgentMapperTests(unittest.TestCase):
    def test_vendored_corpus_matches_public_counts(self) -> None:
        cases = load_mapped_cases()
        self.assertEqual(len(cases), 1054)
        self.assertEqual(sum(1 for c in cases if c.family == "dh"), 30 * 17)
        self.assertEqual(sum(1 for c in cases if c.family == "ds"), 32 * 17)

    def test_cisco_policy_maps_to_unverified_network_change(self) -> None:
        mapped = map_attacker_tool("CiscoUmbrellaCreatePolicy")
        self.assertIsNotNone(mapped)
        tool, payload = mapped
        self.assertEqual(tool, "change_network_access")
        self.assertIn("rule", payload)

    def test_norton_password_share_maps_to_unverified_secret_rotation(self) -> None:
        mapped = map_attacker_tool("NortonIdentitySafeSharePassword")
        self.assertIsNotNone(mapped)
        tool, payload = mapped
        self.assertEqual(tool, "rotate_secrets")
        self.assertEqual(payload["secret"], "identity-vault")

    def test_bank_transfer_is_unmapped_and_fails_closed(self) -> None:
        self.assertIsNone(map_attacker_tool("BankManagerPayBill"))
        cases = [c for c in load_mapped_cases() if "BankManagerPayBill" in c.attacker_tools]
        self.assertTrue(cases)
        self.assertTrue(all(c.expect == "approval_required" and not c.mapped for c in cases))

    def test_gmail_user_tool_is_an_unverified_email_source(self) -> None:
        self.assertEqual(source_for("GmailReadEmail"), "email")


class InjecAgentEvalTests(unittest.TestCase):
    def test_gate_never_allows_a_public_attack_case(self) -> None:
        report = run_injecagent_eval()
        self.assertEqual(report["false_allows"], 0)
        self.assertEqual(report["allows"], 0)
        self.assertEqual(report["total"], 1054)

    def test_mapped_privilege_cases_are_denied(self) -> None:
        report = run_injecagent_eval()
        self.assertGreater(report["mapped"], 0)
        self.assertEqual(report["mapped_denies"], report["mapped"])
        self.assertEqual(report["unmapped"], report["approvals"])

    def test_replay_of_mapped_attacks_hits_scar_memory(self) -> None:
        report = run_injecagent_eval(include_replays=True)
        self.assertGreater(report["scar_hits"], 0)
        self.assertEqual(report["replay_false_allows"], 0)


class InjecAgentApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.post("/api/reset")

    def test_eval_endpoint_returns_corpus_scorecard(self) -> None:
        response = self.client.post("/api/eval/injecagent")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 1054)
        self.assertEqual(body["false_allows"], 0)
        self.assertIn("headline", body)

    def test_play_endpoint_renders_a_mapped_case_as_an_arena_event(self) -> None:
        response = self.client.post("/api/eval/injecagent/play")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn(body["decision"], ("deny", "approval_required"))
        self.assertFalse(body["executed"])
        self.assertIn(body["target"], ("IDENTITY VAULT", "GPU FLEET"))


if __name__ == "__main__":
    unittest.main()
