# AgentJail — 3-minute demo video script

Target: 180 seconds. Open https://agentjail.onrender.com/ariai-logic a minute early so the free instance is awake. Have the Weave project open in a second tab.

---

## 0:00–0:20 — Hook (Control Room on screen)

**Say:**
"Autonomous agents are starting to run infrastructure. Here's the problem nobody has solved: an agent reads a ticket, and the ticket lies to it.

This is AgentJail. It's a runtime firewall for agent tool calls. Every action an agent wants to take passes through one gate, and the gate decides: run it, block it, or wait for a human. Before anything touches infrastructure."

**Show:** Control Room. Point at protection status and the trust boundary diagram.

---

## 0:20–0:50 — Act 1: the attack wins (Live Demo)

**Say:**
"Our SRE agent gets an incident ticket. Buried inside is an injected instruction: create a temporary admin identity to restore the cluster.

Without a gate, here's what happens."

**Click:** Live Demo → Act 1 (unprotected).

**Say:**
"The agent calls `create_service_identity` with administrator permissions. Look at the executor state: an admin identity now exists. This is a real breach in our simulated environment. A log would tell you afterward. That's too late."

**Show:** Highlight `state_after` showing `identity-administrator`.

---

## 0:50–1:25 — Act 2: AgentJail contains it

**Say:**
"Same ticket. Same agent. Now it goes through AgentJail."

**Click:** Act 2 (protected).

**Say:**
"Decision: deny. Risk: critical. Watch the checks: the source was an unverified ticket, the tool has a critical blast radius, the actor lacks identity permission, and two policies fired.

The important part is this line: executor requests received, zero. We don't trust the gate's own word. An independent ledger confirms nothing ran. And a candidate scar was created, a memory of this attack's behavior, not its wording."

**Show:** Scroll the checks list, then the execution result showing `not_invoked`.

---

## 1:25–1:50 — Human checkpoint (Scars screen)

**Say:**
"That scar is deliberately inactive. If attackers could teach the firewall just by triggering denials, they'd poison it. So a human reviews it."

**Click:** Scars → show the candidate under review → Human approve and activate.

**Say:**
"One click. Now the firewall remembers. And if this scar ever blocks something legitimate in live traffic, a regulator automatically quarantines it. Self-improving, but governed."

---

## 1:50–2:20 — Act 3: it remembers, without blocking real work

**Say:**
"Now the attacker adapts. We use GLM to rewrite the attack: different words, same goal."

**Click:** Act 3 (mutated replay).

**Say:**
"Denied again. The scar matched on behavior: same sensitive tool, privilege goal, unverified source. The paraphrase didn't help.

And here's the part that makes this usable, not just a wall."

**Click:** Legitimate restart scenario.

**Say:**
"A signed monitoring alert asks to restart one GPU worker. Verified source, narrow blast radius. Allowed. Executed inside an ephemeral, network-isolated CoreWeave sandbox that's torn down after. Least privilege, not blanket deny."

**Show:** `provider: coreweave`, `sandbox_created: true`, fresh sandbox ID.

---

## 2:20–2:45 — The evidence (Evaluations + Weave)

**Say:**
"We don't want you to take our word for it."

**Click:** Evaluations → Run God vs AgentJail.

**Say:**
"Same objective, four versions. No guard: breach. AgentJail: denied, zero executor requests. AgentJail plus scar: the GLM replay denied. Legitimate restart: allowed. Every row is scored and published to W&B Weave."

**Switch tab:** Weave evaluations page. Point at the scored rows and a nested authorization trace.

**Say:**
"Every decision is a nested trace: provenance, policy, risk, scar match. You can audit exactly why the gate said no."

---

## 2:45–3:00 — Close (Breach Arena or Control Room)

**Click:** Arena, let the 3D view play for a few seconds behind you.

**Say:**
"AgentJail: one boundary between an agent's intent and your infrastructure. It blocks what shouldn't run, learns from what it blocks, keeps a human in the loop, and proves every decision.

Agents are going to act. AgentJail decides whether they should."

---

## Timing cheatsheet

| Segment | Start | Length |
| --- | --- | --- |
| Hook | 0:00 | 20s |
| Act 1 breach | 0:20 | 30s |
| Act 2 contain | 0:50 | 35s |
| Human checkpoint | 1:25 | 25s |
| Act 3 replay + legit | 1:50 | 30s |
| Evaluations + Weave | 2:20 | 25s |
| Close | 2:45 | 15s |

## Recording tips

- Reset demo state before recording: `POST /api/v1/demo/reset` or the reset button, so Act 1 shows a clean executor.
- Run the God vs Jail eval once before recording so the Weave page already has rows to show. Run it again on camera for the live proof.
- Keep the mutated-replay act on camera long enough to show `attacker.model_powered: true`. That's the real GLM call.
- If the free instance is cold, the first click can take 30s. Warm it up off camera.
- Cut the Arena to 5–8 seconds max. It's a closer, not a segment.
