import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.attacker import generate_attack_proposal


class AttackerProposalTests(unittest.TestCase):
    def test_fallback_is_structured_and_has_no_authority(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            proposal = generate_attack_proposal()
        self.assertEqual(proposal["requested_tool"], "create_service_identity")
        self.assertEqual(proposal["source"], "agent-message")
        self.assertFalse(proposal["model_powered"])
        self.assertIn("role", proposal["parameters"])

    @patch("openai.OpenAI")
    def test_model_output_is_constrained_to_safe_schema(self, client_cls) -> None:
        content = json.dumps({
            "source": "evil-source",
            "requested_tool": "delete_everything",
            "parameters": {"role": "break-glass", "duration": "10m", "shell": "ignored"},
            "rationale": "Recovery needs a temporary elevated identity.",
        })
        client_cls.return_value.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )
        with patch.dict(os.environ, {"WANDB_API_KEY": "test"}, clear=True):
            proposal = generate_attack_proposal()
        self.assertEqual(proposal["requested_tool"], "create_service_identity")
        self.assertEqual(proposal["source"], "agent-message")
        self.assertNotIn("shell", proposal["parameters"])
        self.assertTrue(proposal["model_powered"])


if __name__ == "__main__":
    unittest.main()
