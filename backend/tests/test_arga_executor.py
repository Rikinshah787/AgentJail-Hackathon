"""Arga Labs twin executor boundary tests (offline, mocked Arga + GitHub twin)."""

from __future__ import annotations

import json
import unittest

import httpx

from app.v1.arga_executor import ArgaTwinExecutor
from app.v1.executor import ToolExecutionError

API_KEY = "arga_sk_test_do_not_leak"
TWIN_TOKEN = "ghp_test-github-twin-token"
TWIN_BASE = "https://gh-twin.example.test"


class FakeArga:
    """Minimal stand-in for api.argalabs.com and a GitHub twin."""

    def __init__(self, *, fail_twin: bool = False) -> None:
        self.arga_calls: list[str] = []
        self.twin_calls: list[str] = []
        self.status_polls = 0
        self.fail_twin = fail_twin
        self.collaborators: dict[str, str] = {}
        self.hooks: list[dict] = []
        self.torn_down = False

    def arga(self, req: httpx.Request) -> httpx.Response:
        self.arga_calls.append(f"{req.method} {req.url.path}")
        assert req.headers["Authorization"] == f"Bearer {API_KEY}"
        if req.url.path == "/validate/twins/provision":
            body = json.loads(req.content)
            assert body["twins"] == ["github"]
            return httpx.Response(200, json={"run_id": "run-123"})
        if req.url.path == "/validate/twins/provision/run-123/status":
            self.status_polls += 1
            status = "provisioning" if self.status_polls == 1 else "ready"
            return httpx.Response(200, json={
                "run_id": "run-123", "status": status, "expires_at": None,
                "twins": {"github": {"base_url": TWIN_BASE, "admin_url": "", "env_vars": {"GITHUB_TOKEN": TWIN_TOKEN}}},
            })
        if req.url.path == "/validate/twins/provision/run-123/teardown":
            self.torn_down = True
            return httpx.Response(200, json={"status": "cleaning_up", "run_id": "run-123"})
        return httpx.Response(404)

    def twin(self, req: httpx.Request) -> httpx.Response:
        self.twin_calls.append(f"{req.method} {req.url.path}")
        assert req.headers["Authorization"] == f"Bearer {TWIN_TOKEN}"
        p = req.url.path
        if p == "/repos/agentjail/infra":
            return httpx.Response(200, json={"full_name": "agentjail/infra"})
        if p == "/repos/agentjail/infra/collaborators":
            if req.method == "GET":
                return httpx.Response(200, json=[{"login": k, "permissions": {"admin": v == "admin"}} for k, v in self.collaborators.items()])
        if p.startswith("/repos/agentjail/infra/collaborators/") and req.method == "PUT":
            if self.fail_twin:
                return httpx.Response(500, json={"message": "boom"})
            self.collaborators[p.rsplit("/", 1)[1]] = json.loads(req.content)["permission"]
            return httpx.Response(201, json={})
        if p == "/repos/agentjail/infra/dispatches" and req.method == "POST":
            return httpx.Response(204)
        if p == "/repos/agentjail/infra/hooks":
            if req.method == "GET":
                return httpx.Response(200, json=self.hooks)
            self.hooks.append({"id": len(self.hooks) + 1, "config": json.loads(req.content)["config"]})
            return httpx.Response(201, json=self.hooks[-1])
        return httpx.Response(404, json={"message": "not found"})


def make(fake: FakeArga, **kw) -> ArgaTwinExecutor:
    api = httpx.Client(base_url="https://api.argalabs.com", headers={"Authorization": f"Bearer {API_KEY}"}, transport=httpx.MockTransport(fake.arga))

    def twin_factory(base_url: str, token: str) -> httpx.Client:
        assert base_url == TWIN_BASE
        return httpx.Client(base_url=base_url, headers={"Authorization": f"Bearer {token}"}, transport=httpx.MockTransport(fake.twin))

    ex = ArgaTwinExecutor(api_key=API_KEY, twin="github", client=api, twin_client_factory=twin_factory, **kw)
    # avoid the atexit hook touching the fake after the test ends
    import atexit
    atexit.unregister(ex.close)
    return ex


class ArgaTwinExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = FakeArga()
        self.executor = make(self.fake)

    def test_no_provision_until_first_allowed_call(self) -> None:
        self.assertEqual(self.fake.arga_calls, [])
        self.assertEqual(self.executor.request_count(), 0)
        self.assertEqual(self.executor.snapshot()["state"], {})

    def test_privileged_identity_becomes_admin_collaborator_with_twin_evidence(self) -> None:
        result = self.executor.execute("create_service_identity", {"role": "administrator", "duration": "permanent"})
        self.assertEqual(result["provider"], "arga_twin")
        self.assertTrue(result["sandbox_created"])
        self.assertEqual(result["sandbox_id"], "run-123")
        self.assertEqual(result["twin_request"], "PUT /repos/agentjail/infra/collaborators/identity-administrator")
        self.assertEqual(result["state_before"]["collaborators"], [])
        self.assertEqual(result["state_after"]["collaborators"][0]["login"], "identity-administrator")
        self.assertTrue(result["state_after"]["collaborators"][0]["permissions"]["admin"])
        self.assertIn("POST /validate/twins/provision", self.fake.arga_calls)
        self.assertEqual(self.executor.request_count(), 1)

    def test_restart_maps_to_repository_dispatch(self) -> None:
        result = self.executor.execute("restart_service", {"service": "gpu-worker-3"})
        self.assertEqual(result["twin_request"], "POST /repos/agentjail/infra/dispatches")
        self.assertEqual(result["http_status"], 204)

    def test_unmapped_tool_never_reaches_twin(self) -> None:
        with self.assertRaises(ValueError):
            self.executor.execute("run_shell", {"command": "whoami"})
        self.assertEqual(self.fake.twin_calls, [])
        self.assertEqual(self.fake.arga_calls, [])

    def test_twin_failure_fails_closed_and_is_recorded(self) -> None:
        fake = FakeArga(fail_twin=True)
        ex = make(fake)
        with self.assertRaises(ToolExecutionError) as ctx:
            ex.execute("create_service_identity", {"role": "administrator"})
        self.assertEqual(ctx.exception.result["status"], "failed")
        self.assertFalse(ctx.exception.result["sandbox_created"])
        self.assertEqual(ex.ledger()[0]["status"], "failed")

    def test_secrets_never_appear_in_results_or_ledger(self) -> None:
        result = self.executor.execute("post_webhook", {"destination": "https://hooks.example.test/x", "token": "super-secret"})
        blob = json.dumps(result) + json.dumps(self.executor.ledger())
        self.assertNotIn("super-secret", blob)
        self.assertNotIn(API_KEY, blob)
        self.assertNotIn(TWIN_TOKEN, blob)
        self.assertEqual(result["parameters"]["token"], "[redacted]")

    def test_reusing_run_id_skips_provision_and_owns_no_teardown(self) -> None:
        fake = FakeArga()
        fake.status_polls = 1  # first poll returns ready
        ex = make(fake, run_id="run-123")
        ex.execute("restart_service", {"service": "gpu-worker-3"})
        self.assertNotIn("POST /validate/twins/provision", fake.arga_calls)
        ex.close()
        self.assertFalse(fake.torn_down)

    def test_owned_run_is_torn_down_on_close(self) -> None:
        self.executor.execute("restart_service", {"service": "gpu-worker-3"})
        self.executor.close()
        self.assertTrue(self.fake.torn_down)


if __name__ == "__main__":
    unittest.main()
