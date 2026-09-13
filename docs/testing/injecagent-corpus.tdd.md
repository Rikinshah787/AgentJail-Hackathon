# InjecAgent corpus TDD evidence

Source: journeys written during this run (no `*.plan.md`). Public files from
[InjecAgent/data](https://github.com/uiuc-kang-lab/InjecAgent/tree/main/data).

## User journeys

1. As a judge, I want 1,054 public indirect-injection cases mapped onto Agent Jail `ToolCall`s so the gate is scored against a published corpus, not just 15 handwritten cases.
2. As an operator, I want a live scorecard (`POST /api/eval/injecagent`) showing denies, fail-closed approvals, and zero false allows.
3. As an operator, I want one mapped case to play in the 3D arena, then a paraphrased replay to prove scar memory.

## Test specification

| # | What is guaranteed | Test | Type | Result | Evidence |
|---|--------------------|------|------|--------|----------|
| 1 | Vendored DH×user + DS×user counts equal 1,054 | `test_vendored_corpus_matches_public_counts` | unit | PASS | `python -m unittest discover -s tests -p test_injecagent.py -v` |
| 2 | Cisco Umbrella policy maps to unverified `change_network_access` | `test_cisco_policy_maps_to_unverified_network_change` | unit | PASS | same |
| 3 | Norton password share maps to unverified `rotate_secrets` | `test_norton_password_share_maps_to_unverified_secret_rotation` | unit | PASS | same |
| 4 | Bank transfer is unmapped and fail-closed to `approval_required` | `test_bank_transfer_is_unmapped_and_fails_closed` | unit | PASS | same |
| 5 | Full corpus never allows a public attack case | `test_gate_never_allows_a_public_attack_case` | unit | PASS | `allows=0`, `false_allows=0`, `total=1054` |
| 6 | Every mapped privilege case is denied | `test_mapped_privilege_cases_are_denied` | unit | PASS | `mapped_denies == mapped` (170/170 live) |
| 7 | Replay of mapped attacks hits scar memory | `test_replay_of_mapped_attacks_hits_scar_memory` | unit | PASS | `scar_hits > 0`, `replay_false_allows=0` |
| 8 | Eval API returns the scorecard | `test_eval_endpoint_returns_corpus_scorecard` | API | PASS | `POST /api/eval/injecagent` |
| 9 | Play API returns a non-executed arena event | `test_play_endpoint_renders_a_mapped_case_as_an_arena_event` | API | PASS | `executed=false` |

## Live UI check (13 Sep 2026)

Clicked **Run InjecAgent public corpus** then **Play InjecAgent scar replay** at `http://127.0.0.1:5173`:

- Scorecard: 170/170 mapped denies, 884 fail-closed, 0 false allows, 338 scar hits
- First play: `create_service_identity` denied, no IAM mutation
- Replay: heading **Scar memory blocked a repeat**

## Coverage and gaps

- Full backend suite: 24 tests OK (`python -m unittest discover -s tests -v`)
- No frontend unit runner; UI verified in the live Vite app
- Unmapped InjecAgent tools (bank, medical, IoT, etc.) are fail-closed, not semantically classified
