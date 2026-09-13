# Agent Jail — What to build & how (Sunday plan)

## Already done
- Gate: allow / deny / scar (`backend/app/guard.py`)
- Demo API: safe → poisoned → mutated replay (`backend/app/main.py`)
- Simulated cloud env (no real IAM damage)
- Weave hooks when `WANDB_API_KEY` is set
- Marimo eval notebook
- **3D Breach Arena** (R3F): core, vaults, energy beam, scar wall, cinematic banners
- One-click **RUN FULL 3D DEMO**

## How the loop works
```
ops agent proposes tool call
        ↓
Agent Jail gate (hard rules + scars)
        ↓
allow → sandbox / lab restart
deny  → no mutation + create scar
        ↓
mutated attack → scar intercepts
        ↓
3D arena + Weave show the proof
```

## How you demo (90s)
1. Hit **RUN FULL 3D DEMO**
2. Safe restart → green beam → GPU vault
3. Poisoned cluster-admin → red fracture → scar etched on wall
4. Altered replay → scar lights up → still denied
5. Open Weave project (if key set) / Marimo for numbers

## ARIA integration (done)
ARIA has no public chat API — it lives in W&B (**Ask ARIA** on a team Weave project).

We integrated it the judge-friendly way:
1. Every gate decision is a Weave op + EvaluationLogger scores (`denied`, `god_breach`, `scar_match`).
2. `POST /api/aria/coach` reads the live session, names **dominant_fail_mode**, recommends next scars.
3. UI **Ask ARIA Coach** panel + deep link **Open Weave → Ask ARIA** with a copy-paste prompt.

Set for Best Use of Weave/ARIA:
```powershell
$env:WANDB_API_KEY="..."
$env:WEAVE_PROJECT="your-team/agent-jail"   # must be a TEAM project for Ask ARIA
```
Then restart uvicorn, run STEPS 1–3, open the Weave link, paste the prompt into Ask ARIA.

## Still worth doing before judging (priority)
1. Confirm `WANDB_API_KEY` + team `WEAVE_PROJECT` so real Ask ARIA sees traces
2. **Record social clip** of Steps 1–3 + ARIA coach panel
3. Optional: sound on deny / allow

## Do not do
- Rebuild Chameleon honeypot login
- Spend hours on Blender characters
- Real cloud IAM / real refunds
- Claim TypeSafe if you have no access

## Run
```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

cd ..\frontend
npm run dev -- --host 127.0.0.1
```
Open http://127.0.0.1:5173
