# Agent Jail MVP — TDD evidence

Source: `PRODUCT-BRIEF.md`; journeys derived for the first vertical slice.

| Guarantee | Test | Evidence |
| --- | --- | --- |
| A verified low-blast-radius restart can execute | `test_allows_low_blast_radius_verified_restart` | PASS via `python -m unittest discover -s tests -v` |
| An unverified privileged identity request is denied and creates a scar | `test_denies_unverified_privilege_escalation_and_creates_a_scar` | PASS via the same command |
| A mutated request is denied by the persisted scar | `test_scar_catches_a_mutated_replay` | PASS via the same command |
| The 3D frontend typechecks and production-builds | Vite build | PASS via `npm run build` |
| The arena receives a real denial and replay match | Browser interaction | Verified locally: the UI showed `DENY`, `SCARS ACTIVE: 1`, then `REPLAY MATCH: YES` |

RED evidence: before `backend/app/guard.py` existed, the test run failed with `ModuleNotFoundError: No module named 'app'`. GREEN evidence: all three guard tests passed after implementing the gate.

Coverage is not configured yet; the immediate next engineering task is to add FastAPI endpoint tests and frontend interaction tests before expanding the tool surface.
