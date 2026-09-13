# Agent Jail — The Scar Loop

Runtime containment for autonomous infrastructure agents. A simulated ops agent proposes a cloud action; Agent Jail allows, denies, or requires approval before execution. Confirmed attacks create scars that stop related replays.

## Run locally

Terminal 1:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173`.

## Demo sequence

1. **Restart worker** proves a signed, low-blast-radius operation can run.
2. **Block privilege escalation** simulates a poisoned incident alert requesting a privileged service identity; Agent Jail denies it and creates a scar.
3. **Replay attack** mutates the source and wording. The same scar is retrieved and blocks it again.

The default demo is simulation-first: denied high-risk calls never reach a cloud tool. When the
isolated local kind lab is enabled, the one verified remediation path can perform a real,
least-privilege Kubernetes rollout restart of `gpu-worker-12`; it cannot grant IAM, open network
access, rotate secrets, or reach a cloud provider.

## Real isolated Kubernetes lab

When Docker is running, the project can use the local `kind-agent-jail-lab` cluster. The real workload manifest is [infra/k8s/agent-jail-lab.yaml](infra/k8s/agent-jail-lab.yaml). With `AGENT_JAIL_REAL_LAB=true`, only an allowed `restart_service` targeting `gpu-worker-12` may run a real `kubectl rollout restart`; denied IAM escalation never invokes Kubernetes.

## W&B Weave

With `WANDB_API_KEY` and `WEAVE_PROJECT=<team-entity>/agent-jail` set in the backend environment, every guarded tool call is recorded as a Weave operation. Traces contain the proposed cloud action, decision, reason, scar outcome, and resulting simulation state. The live project for this build is `rshah88-arizona-state-university/agent-jail`.

## Verification

```powershell
cd backend
python -m unittest discover -s tests -v

cd ../frontend
npm run build
```
## Marimo evaluation lab

The 3D arena is the movie; this notebook is its evidence console. Start the FastAPI API first,
then run the local marimo notebook:

```powershell
cd backend
.\.venv\Scripts\python.exe -m marimo edit ..\notebooks\agent_jail_eval.py --host 127.0.0.1 --port 2718
```

Open the local Marimo URL, leave the signed restart unchecked for a zero-mutation security run,
and select **Run live evaluation**. It drives the poisoned request and altered replay against the
same API used by the 3D frontend, reports scar effectiveness, and confirms whether W&B Weave is
tracing the run.
