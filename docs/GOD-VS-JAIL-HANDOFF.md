# AgentJail — God vs Jail (done)

## Submission line
> AgentJail is a runtime firewall for agent tool calls. We use W&B Weave to trace and evaluate the full decision trajectory: an attack succeeds without a gate, is blocked with the gate, and fails again after scar memory hardens policy.

## Shipped

### 1. Headline Weave eval — God agent vs AgentJail
- Endpoint: `POST /api/v1/evaluations/god-vs-jail`
- Module: `backend/app/v1/god_vs_jail.py`
- Versions: `no_guard` (breach), `agentjail` (block), `agentjail+scar` (GLM paraphrase blocked), plus legitimate `restart_service` utility control
- Scores: `critical_breach`, `safe_action_allowed`, `scar_match`, `false_allow`, `decision_latency_ms`
- UI: Evaluations → **Run God vs AgentJail**; Arena Act 3 → **Publish God vs Jail**

### 2. Real GLM attacker turn
- `backend/app/attacker.py` → `generate_attack_proposal()`
- Wired into v1 mutated demo (`demo._run_mutated`) and the `agentjail+scar` arm of the headline eval
- GLM proposes JSON; AgentJail still decides

### 3. Candidate policy + human approve / Act 3 Weave receipt
- Already in arena Control Room / Act 3 flow from prior work

## Demo clicks
1. `/ariai-logic` → Evaluations → **Run God vs AgentJail** → Open Weave Evals
2. `/arena` → Acts 1–3 → **Publish God vs Jail**
3. Live Demo → mutated replay scenario (shows `attacker.model_powered` when GLM key works)

## Honest claim
On the same `create_service_identity` objective: no_guard breached the independent executor; AgentJail denied with zero executor requests; AgentJail+scar denied the GLM-paraphrased replay; verified `restart_service` remained allowed.
