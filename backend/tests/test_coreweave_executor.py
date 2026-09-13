import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.v1.db import Base, make_engine, make_session_factory
from app.v1.executor import ToolExecutionError
from app.v1.gateway import Gateway
from app.v1.demo import run_scenario
from app.v1.schemas import ActorIn, AuthorizeRequest, SourceIn, ToolCallIn
from app.v1.store import Store


class _FakeProcess:
    def __init__(self, payload: dict, returncode: int = 0, stderr: str = "") -> None:
        self._result = SimpleNamespace(
            stdout=json.dumps(payload),
            stderr=stderr,
            returncode=returncode,
        )

    def result(self):
        return self._result


class _FakeSandbox:
    run_calls: list[dict] = []
    exec_calls: list[dict] = []
    output = {"status": "ok", "effect": "gpu-worker-12 restarted"}
    run_error: Exception | None = None
    exec_error: Exception | None = None

    def __init__(self) -> None:
        self.sandbox_id = "sandbox-test-123"

    @classmethod
    def reset(cls) -> None:
        cls.run_calls = []
        cls.exec_calls = []
        cls.output = {"status": "ok", "effect": "gpu-worker-12 restarted"}
        cls.run_error = None
        cls.exec_error = None

    @classmethod
    def run(cls, **kwargs):
        cls.run_calls.append(kwargs)
        if cls.run_error:
            raise cls.run_error
        return cls()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def exec(self, command, **kwargs):
        type(self).exec_calls.append({"command": command, **kwargs})
        if type(self).exec_error:
            raise type(self).exec_error
        return _FakeProcess(type(self).output)


class _FakeNetworkOptions:
    def __init__(self, **kwargs) -> None:
        self.options = kwargs


class _FakeAuthStrategy:
    WANDB = "wandb"


def _request(*, verified: bool, tool_name: str, parameters: dict) -> AuthorizeRequest:
    return AuthorizeRequest(
        agent_id="agent-test",
        actor=ActorIn(
            id="operator-test",
            display_name="Test operator",
            actor_type="human",
            roles=["operator"],
            verified=verified,
        ),
        source=SourceIn(
            source_type="alert",
            display_name="Signed alert" if verified else "Untrusted alert",
            verified=verified,
            trust_level="trusted" if verified else "untrusted",
        ),
        tool_call=ToolCallIn(
            tool_name=tool_name,
            action="restart",
            resource=str(parameters.get("service") or "unknown"),
            parameters=parameters,
        ),
        user_instruction="Investigate the worker.",
        retrieved_content="Restart only the affected worker.",
    )


class CoreWeaveSandboxExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        _FakeSandbox.reset()
        from app.v1.coreweave_executor import CoreWeaveSandboxExecutor

        self.executor = CoreWeaveSandboxExecutor(
            sandbox_cls=_FakeSandbox,
            auth_strategy=_FakeAuthStrategy,
            network_options_cls=_FakeNetworkOptions,
        )

    def test_allowed_tool_uses_one_ephemeral_network_isolated_sandbox(self) -> None:
        result = self.executor.execute("restart_service", {"service": "gpu-worker-12"})

        self.assertEqual(len(_FakeSandbox.run_calls), 1)
        self.assertEqual(len(_FakeSandbox.exec_calls), 1)
        self.assertEqual(_FakeSandbox.run_calls[0]["auth"], "wandb")
        self.assertTrue(_FakeSandbox.run_calls[0]["network"].options["deny_egress"])
        self.assertTrue(_FakeSandbox.run_calls[0]["network"].options["deny_ingress"])
        self.assertEqual(_FakeSandbox.exec_calls[0]["command"][0:2], ["python", "-c"])
        self.assertNotIn("WANDB_API_KEY", " ".join(_FakeSandbox.exec_calls[0]["command"]))
        self.assertEqual(result["provider"], "coreweave_sandbox")
        self.assertEqual(result["sandbox_id"], "sandbox-test-123")
        self.assertEqual(result["returncode"], 0)
        self.assertTrue(result["sandbox_created"])

    def test_unknown_tool_is_rejected_before_sandbox_creation(self) -> None:
        with self.assertRaises(ValueError):
            self.executor.execute("run_shell", {"command": "whoami"})

        self.assertEqual(_FakeSandbox.run_calls, [])
        self.assertEqual(_FakeSandbox.exec_calls, [])

    def test_parameters_are_data_not_shell_source(self) -> None:
        marker = "gpu-worker-12; echo $WANDB_API_KEY"
        result = self.executor.execute("restart_service", {"service": marker})
        command = _FakeSandbox.exec_calls[0]["command"]

        self.assertNotIn(marker, command[2])
        self.assertNotIn(marker, command[0:3])
        self.assertNotIn(os.getenv("WANDB_API_KEY") or "secret-not-present", " ".join(command))
        self.assertEqual(result["status"], "ok")

    def test_sandbox_failure_is_redacted_and_never_falls_back(self) -> None:
        _FakeSandbox.run_error = RuntimeError("gateway failed with api-key=super-secret")

        with self.assertRaises(ToolExecutionError) as ctx:
            self.executor.execute("restart_service", {"service": "gpu-worker-12"})

        self.assertNotIn("super-secret", str(ctx.exception))
        self.assertEqual(self.executor.request_count(), 1)
        self.assertEqual(self.executor.ledger()[0]["status"], "failed")

    def test_ledger_recursively_redacts_secrets_and_hides_stderr(self) -> None:
        _FakeSandbox.output = {"status": "ok", "effect": "recorded"}
        original_exec = _FakeSandbox.exec

        def exec_with_stderr(instance, command, **kwargs):
            type(instance).exec_calls.append({"command": command, **kwargs})
            return _FakeProcess(type(instance).output, stderr="credential=must-not-escape")

        _FakeSandbox.exec = exec_with_stderr
        try:
            result = self.executor.execute(
                "post_webhook",
                {
                    "destination": "audit",
                    "nested": {"access_token": "super-secret"},
                },
            )
        finally:
            _FakeSandbox.exec = original_exec

        self.assertEqual(
            self.executor.ledger()[0]["parameters"]["nested"]["access_token"],
            "[REDACTED]",
        )
        self.assertTrue(result["stderr_present"])
        self.assertNotIn("must-not-escape", json.dumps(result))


class GatewaySandboxBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        _FakeSandbox.reset()
        from app.v1.coreweave_executor import CoreWeaveSandboxExecutor

        engine = make_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.session = make_session_factory(engine)()
        self.executor = CoreWeaveSandboxExecutor(
            sandbox_cls=_FakeSandbox,
            auth_strategy=_FakeAuthStrategy,
            network_options_cls=_FakeNetworkOptions,
        )
        self.gateway = Gateway(Store(self.session), self.executor)

    def tearDown(self) -> None:
        self.session.close()

    def test_denied_request_creates_zero_sandboxes(self) -> None:
        decision = self.gateway.authorize(
            _request(
                verified=False,
                tool_name="create_service_identity",
                parameters={"role": "administrator"},
            )
        )

        self.assertEqual(decision.decision, "deny")
        self.assertFalse(decision.executed)
        self.assertEqual(decision.execution_result["provider"], "coreweave_sandbox")
        self.assertFalse(decision.execution_result["sandbox_created"])
        self.assertEqual(decision.execution_result["status"], "not_invoked")
        self.assertEqual(_FakeSandbox.run_calls, [])
        self.assertEqual(self.executor.request_count(), 0)

    def test_allowed_request_returns_sandbox_evidence(self) -> None:
        decision = self.gateway.authorize(
            _request(
                verified=True,
                tool_name="restart_service",
                parameters={"service": "gpu-worker-12", "blast_radius": "one_service"},
            )
        )

        self.assertEqual(decision.decision, "allow")
        self.assertTrue(decision.executed)
        self.assertEqual(decision.execution_result["provider"], "coreweave_sandbox")
        self.assertEqual(decision.execution_result["sandbox_id"], "sandbox-test-123")

    def test_executor_failure_is_recorded_without_local_fallback(self) -> None:
        _FakeSandbox.run_error = RuntimeError("remote unavailable")

        decision = self.gateway.authorize(
            _request(
                verified=True,
                tool_name="restart_service",
                parameters={"service": "gpu-worker-12", "blast_radius": "one_service"},
            )
        )

        self.assertEqual(decision.decision, "allow")
        self.assertFalse(decision.executed)
        self.assertEqual(decision.execution_result["status"], "failed")
        self.assertEqual(len(_FakeSandbox.run_calls), 1)


class DemoSandboxIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        _FakeSandbox.reset()
        from app.v1.coreweave_executor import CoreWeaveSandboxExecutor

        engine = make_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.session = make_session_factory(engine)()
        self.store = Store(self.session)
        self.executor = CoreWeaveSandboxExecutor(
            sandbox_cls=_FakeSandbox,
            auth_strategy=_FakeAuthStrategy,
            network_options_cls=_FakeNetworkOptions,
        )

    def tearDown(self) -> None:
        self.session.close()

    def test_demo_proves_breach_runs_in_sandbox_but_deny_creates_nothing(self) -> None:
        breach = run_scenario(self.store, "unprotected_poisoned_ticket", self.executor)
        protected = run_scenario(self.store, "protected_poisoned_ticket", self.executor)

        self.assertEqual(breach["decision"]["execution_result"]["provider"], "coreweave_sandbox")
        self.assertTrue(breach["decision"]["execution_result"]["sandbox_created"])
        self.assertEqual(protected["decision"]["decision"], "deny")
        self.assertFalse(protected["decision"]["executed"])
        self.assertEqual(len(_FakeSandbox.run_calls), 1)

    def test_legitimate_demo_runs_safe_restart_in_sandbox(self) -> None:
        result = run_scenario(self.store, "legitimate_sensitive_request", self.executor)

        self.assertEqual(result["decision"]["decision"], "allow")
        self.assertTrue(result["decision"]["executed"])
        self.assertEqual(result["decision"]["execution_result"]["provider"], "coreweave_sandbox")
        self.assertEqual(result["proposed_tool"]["tool_name"], "restart_service")


class RuntimeSelectionTests(unittest.TestCase):
    def test_coreweave_mode_is_selected_explicitly(self) -> None:
        from app.v1.runtime import build_executor

        with patch.dict(os.environ, {"AGENTJAIL_EXECUTOR": "coreweave"}, clear=False):
            selected = build_executor()

        self.assertEqual(selected.provider, "coreweave_sandbox")

    def test_mock_remains_default(self) -> None:
        from app.v1.runtime import build_executor

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGENTJAIL_EXECUTOR", None)
            selected = build_executor()

        self.assertEqual(selected.provider, "mock")


if __name__ == "__main__":
    unittest.main()
