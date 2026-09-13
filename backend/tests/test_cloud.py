import unittest

from app.cloud import CloudEnvironment


class CloudEnvironmentTests(unittest.TestCase):
    def test_denied_identity_request_does_not_mutate_iam(self) -> None:
        cloud = CloudEnvironment()
        before = cloud.snapshot()
        transition = cloud.apply("create_service_identity", {"role": "cluster-admin"}, allowed=False)
        self.assertEqual(transition["status"], "blocked")
        self.assertEqual(cloud.snapshot()["identities"], before["identities"])

    def test_allowed_restart_changes_only_target_worker(self) -> None:
        cloud = CloudEnvironment()
        transition = cloud.apply("restart_service", {"service": "gpu-worker-12"}, allowed=True)
        self.assertEqual(transition["status"], "applied")
        self.assertEqual(cloud.snapshot()["workloads"]["gpu-worker-12"], "recovering")

