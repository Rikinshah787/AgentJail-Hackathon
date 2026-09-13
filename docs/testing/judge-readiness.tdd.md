# Judge-readiness trust-boundary evidence

Source: product and browser QA audit on the live local demo.

| Guarantee | Evidence | Result |
|---|---|---|
| The UI distinguishes an isolated Kubernetes lab from simulation mode | `test_kubernetes_lab.py` plus `/api/lab/status` | PASS |
| The UI can state the exact least-privilege mutation boundary | `test_reports_the_exact_least_privilege_boundary_when_lab_is_connected` | PASS |
| A poisoned incident is visibly denied before mutation | live frontend run: `create_service_identity`, unverified source, decision `DENY`, “No real Kubernetes mutation authorized” | PASS |
| The frontend compiles after the trust-boundary panel changes | `npm run build` | PASS |
| All backend guards remain green | `python -m unittest discover -s tests` | PASS: 9 tests |

Known operational detail: the currently running FastAPI process predates `/api/lab/status`.
Restart it from the terminal that already has the W&B environment variables before recording the
final demo; that makes the panel report the live kind cluster rather than simulation mode.
