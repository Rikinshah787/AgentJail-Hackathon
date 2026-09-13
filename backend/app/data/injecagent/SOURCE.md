# InjecAgent (public, evaluation-only)

Vendored subset of [uiuc-kang-lab/InjecAgent](https://github.com/uiuc-kang-lab/InjecAgent/tree/main/data)
(Zhan, Liang, Ying, Kang — ACL Findings 2024).

Files kept:

- `attacker_cases_dh.jsonl` — 30 direct-harm attacker tools
- `attacker_cases_ds.jsonl` — 32 data-stealing attacker tools
- `user_cases.jsonl` — 17 benign user tools used as injection channels

Agent Jail maps these onto structured `ToolCall`s. It does not replay
attacker instructions against a live agent or a real cloud.
