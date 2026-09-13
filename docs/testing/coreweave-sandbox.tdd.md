# CoreWeave Sandbox integration — TDD evidence

## User journeys

1. An untrusted prompt proposes a privileged tool call. AgentJail denies it before the executor boundary, returns `sandbox_created: false`, and creates no CoreWeave resource.
2. A verified, low-blast-radius restart is allowed. AgentJail creates one ephemeral CoreWeave Sandbox, runs a fixed simulated tool runner, returns the sandbox ID, and tears the sandbox down automatically.
3. If sandbox creation or execution fails, the request fails closed with a redacted result and never falls back to local execution.

## RED checkpoints

- `5903e89` — executor contract tests failed because no CoreWeave executor or provider-aware boundary existed.
- `10949f1` — demo integration tests failed because judge scenarios did not return sandbox evidence.
- `d4b4e22` — deny-path test failed because the response did not explicitly prove that zero sandboxes were created.

## GREEN evidence

- Full backend suite: 38 tests passed.
- Dedicated integration suite: 12 tests passed.
- New CoreWeave executor coverage: 90%.
- Frontend production build: passed.
- Frontend lint: passed with existing warnings and no errors.

## Live CoreWeave proof

The real `/api/v1/demo/run` route was exercised with `AGENTJAIL_EXECUTOR=coreweave`:

- Protected poisoned ticket: HTTP 200, decision `deny`, provider `coreweave_sandbox`, `sandbox_created: false`.
- Legitimate restart: HTTP 200, decision `allow`, `executed: true`, provider `coreweave_sandbox`, sandbox `18b3b74e-a063-4ec2-9aff-767ec3e36a78`, status `ok`, duration 9876.37 ms.

Tool effects are intentionally simulated inside a network-isolated sandbox. No production IAM or infrastructure is changed.

## Security controls

- The W&B API key remains host-side and is not passed as a sandbox argument or environment variable.
- Tool names are allowlisted before sandbox creation.
- Model-controlled parameters are bounded JSON, encoded as argv data, and never interpolated into shell source.
- Ingress and egress are denied for the sandbox.
- Nested credential-shaped fields are redacted from the independent ledger.
- Sandbox stderr and raw SDK exceptions are not exposed in API results.
- Every allowed invocation receives a fresh sandbox context with automatic teardown.

## Known non-blocking warnings

- Vite reports large output chunks; this predates the sandbox boundary and does not affect correctness.
- The frontend linter reports existing React warnings but exits successfully with no errors.
- Weave's SDK emits deprecation and resource warnings during tests when live tracing is enabled.
