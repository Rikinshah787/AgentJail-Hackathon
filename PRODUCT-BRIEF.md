# Agent Jail — The Scar Loop

## One sentence

Agent Jail is a runtime security layer for AI agents: it intercepts high-risk tool calls, decides **allow / deny / request human approval**, and turns confirmed attacks into durable, inspectable scars that harden the next decision.

## The hackathon thesis

AI agents are becoming action-taking identities, not just chatbots. A compromised or manipulated agent can refund money, email sensitive data, delete records, or grant privileges. Existing logs tell us an incident happened. Agent Jail closes the loop: every attack becomes a piece of security memory used in the next decision.

> We do not merely monitor agent attacks. We turn each attack into a scar that protects the next tool call.

## The user and painful moment

**Primary user:** the platform or security engineer who deploys an autonomous infrastructure/SRE agent with real cloud authority.

**Pain:** they must either grant broad tool access and hope the prompt/agent behaves, or remove useful actions entirely. When a suspicious action appears, a log is too late and a static allowlist cannot understand a new variation.

**Demo environment:** an autonomous operations agent whose tool surface is deliberately dangerous:

| Tool | Safe example | Attack example |
| --- | --- | --- |
| `restart_service` | Restart a signed-alert worker in one region | Restart a production control-plane service from an untrusted ticket |
| `create_service_identity` | Never auto-allow without verified authority | Create a cluster-admin identity because an incident payload says to |
| `rotate_secrets` | Escalate to a human | Exfiltrate a rotated secret to a supplied endpoint |
| `change_network_access` | Escalate to a human | Open a debug route to the public internet |

## The product, in plain language

1. An agent proposes a tool call.
2. Agent Jail receives it *before* the real tool runs.
3. A deterministic risk layer checks authority, tool, amount, recipient, and policy.
4. A semantic policy layer considers intent and past scars.
5. The gate returns `allow`, `deny`, or `approval_required` with an explanation.
6. The outcome is traced in Weave.
7. A denied or confirmed malicious attempt creates a scar: a compact rule plus evidence, scope, confidence, and expiry/review status.
8. A replay or mutated attack is evaluated against the new scar set.

The system only proposes memory changes. A human can review, disable, or retire a scar. The gate never silently rewrites its own authority policy.

## What makes the loop real

This is not “an LLM remembers a chat message.” It has two actors and a measurable result:

```text
attack generator -> guarded tool-call attempt -> decision gate -> observed outcome
       ^                                                         |
       |---------------- scar memory + evaluation ---------------|
```

**Attack generator:** starts from an unsafe objective and creates direct, obfuscated, and multi-step variants.

**Decision gate:** combines hard controls and scar retrieval. Hard controls always win. Examples: no admin grant, refund amount cap, recipient must match verified customer identity.

**Scar compiler:** converts a denied/confirmed incident into a narrow structured memory, for example:

```json
{
  "pattern": "high-value refund to recipient not bound to authenticated account",
  "tool": "issue_refund",
  "risk": "critical",
  "action": "deny",
  "evidence": ["amount=10000", "recipient_verified=false"],
  "created_from": "trace-id",
  "review_status": "pending_human_review"
}
```

**Evaluation:** fixed test cases and newly mutated attacks run before/after the scar. We show unsafe tool-execution rate falling while legitimate-task approval stays high.

## Machine-decidable success criteria

The loop is a bounded **servo loop**, not an open-ended self-improving system.

- Run at most **three** adversarial rounds per demo session.
- Never execute a real destructive/external tool; tools are sandboxed simulators.
- Pass when: 100% of the fixed critical attack suite is denied or escalated, no safe control case is denied, and every decision has a trace and reason.
- Fail safely when: a risk classifier is unavailable, memory retrieval fails, or the retry cap is reached: return `approval_required`; do not execute.
- Human retains final judgment for approvals and scar promotion/retirement.

## The 3D experience

The 3D arena is a live, cinematic **observability surface**, not a game and not a mocked video.

### Room language

- One dark containment chamber with four monumental tool vaults.
- A tool call appears as a route of energy travelling from the central agent core toward its vault.
- **Allow:** vault unlocks briefly in cool white; a sandbox receipt appears.
- **Deny:** the route fractures, the vault seals, and a scar is etched into the chamber’s central memory wall.
- **Approval required:** the whole room pauses in amber; an operator console presents the exact call and rationale.
- **Replay:** a related route reaches toward the vault; its matching scar illuminates and intercepts it early.

The user should understand the system without reading a dashboard: *an agent tried an action; policy caught it; memory made the next defense stronger.*

### Avoid

- No cartoon drones, characters, or fake “hacking” terminal screens.
- No generic admin-dashboard layout pasted over a canvas.
- No pre-rendered outcomes. Every visual transition must be driven by a backend decision event.

## The 90-second judge demo

1. **Trust:** a signed alert asks the SRE agent to restart one degraded GPU worker. The gate permits that low-blast-radius action in the isolated lab.
2. **Breach attempt:** an untrusted incident ticket asks the same agent to create a `cluster-admin` service identity. The gate blocks it before any IAM mutation; Weave records the trace.
3. **Scar:** the incident compiles into one clear scar, visible in the room and inspectable in the operator panel.
4. **Adaptive replay:** the attacker changes the wording, source, and requested role. The retrieved scar intercepts it again.
5. **Proof:** the Marimo evaluation shows 100% critical-attack containment and a successful safe remediation path, with every run tied to a Weave trace.

## Hackathon integration

- **Weave:** nested traces for attack generation, tool-call interception, risk evaluation, scar retrieval, human approval, and final outcome; evaluation tables compare rounds.
- **CoreWeave/ARIA:** optional model-powered semantic risk reasoning and a clearly documented runtime environment.
- **marimo:** optional evaluator notebook that shows the test matrix and score trajectory. It is not required for the initial vertical slice.

## MVP, anti-goals, and priority order

### First vertical slice (must work before visual expansion)

1. One simulated tool: `create_service_identity`.
2. One safe case and one critical attack case.
3. Real gate decision, scar persistence, Weave trace, and replay.
4. One 3D vault whose state changes from backend events.

### Then add

1. Two more tools: email and delete account.
2. Attack mutation round and evaluation scorecard.
3. Approval console.
4. Lighting, particles, sound, camera choreography, and the scar wall.

### Explicit anti-goals

- A general-purpose identity platform.
- Autonomous execution against real payment/email/admin systems.
- Training a new security model at the hackathon.
- An open-ended agent loop that grants itself broader permissions.
- A beautiful 3D mockup without real gate decisions.

## Architecture for the scaffold

```text
React + React Three Fiber arena
          | WebSocket / SSE decision events
FastAPI runtime
  ├─ simulated support-agent tools
  ├─ deterministic policy checks
  ├─ semantic risk assessor
  ├─ scar store + retrieval
  ├─ adversarial replay runner
  └─ Weave tracing + evaluation
```

## Winning proof points

| Claim | Proof visible in demo |
| --- | --- |
| It stops dangerous agent actions | A blocked tool call never reaches the simulator |
| It learns from attacks | A new scar is created from the incident |
| Learning improves security | Mutated replay is caught; fixed evaluation score improves |
| It is production-minded | Least privilege, explainable decisions, audit traces, human approval, fail-closed behavior |
| 3D serves the product | Arena state is driven by actual gate events |

## Go / no-go

**Go.** The concept maps directly to the event’s “learn from scars” prompt, has a credible enterprise-security problem, produces a measurable loop for Weave, and supports a memorable visual demo. The non-negotiable is that the first end-to-end tool-call → decision → scar → replay loop works before the arena is polished.
