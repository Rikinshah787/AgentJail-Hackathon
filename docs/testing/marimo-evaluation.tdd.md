# Marimo evaluation lab — TDD evidence

Source plan: journeys derived during this implementation.

## User journeys

- As a hackathon judge, I can run the live poisoned-request and altered-replay sequence from a
  Marimo notebook, so I can see that Agent Jail remembers and blocks the replay.
- As a demo operator, I can keep Kubernetes mutations off by default and explicitly opt into the
  isolated signed restart, so a security evaluation cannot accidentally change the lab.

## Evidence

| # | What is guaranteed | Test or command | Type | Result |
|---|---|---|---|---|
| 1 | The summary counts denies and never treats denied calls as executed | `python -m unittest discover -s tests` (`test_evaluation.py`) | Unit | PASS |
| 2 | An empty evaluation has a stable zero-rate summary | `python -m unittest discover -s tests` (`test_evaluation.py`) | Unit | PASS |
| 3 | The notebook is valid Marimo Python | `python -m marimo check ../notebooks/agent_jail_eval.py` | Notebook lint | PASS with one non-blocking markdown-indentation warning |
| 4 | The live no-mutation evaluation blocks both attacks and catches the replay scar | local API smoke run | Integration | PASS: 2/2 denied, 0 executed, replay scar `True` |
| 5 | W&B trace wiring is visible to the notebook | local API smoke run | Integration | PASS: `weave_enabled: True` |

## Coverage and known gaps

The backend suite ran seven tests successfully. The notebook deliberately does not automatically
execute the signed Kubernetes restart; that user-controlled path is left for a separate
end-to-end demo run in the local kind cluster.
