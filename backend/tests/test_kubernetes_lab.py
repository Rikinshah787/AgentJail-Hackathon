import os
import unittest
from subprocess import CompletedProcess
from unittest.mock import patch

from app.kubernetes_lab import lab_status


class KubernetesLabStatusTests(unittest.TestCase):
    def test_reports_the_exact_least_privilege_boundary_when_lab_is_connected(self) -> None:
        with patch.dict(os.environ, {"AGENT_JAIL_REAL_LAB": "true"}, clear=False), patch(
            "app.kubernetes_lab.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=0, stdout="1/1", stderr=""),
        ):
            status = lab_status()

        self.assertTrue(status["connected"])
        self.assertEqual(status["mode"], "isolated_kubernetes")
        self.assertEqual(status["workload_ready"], "1/1")
        self.assertIn("gpu-worker-12", status["mutation_scope"])

    def test_reports_simulation_when_real_lab_is_not_enabled(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            status = lab_status()

        self.assertFalse(status["connected"])
        self.assertEqual(status["mode"], "simulation")


if __name__ == "__main__":
    unittest.main()
