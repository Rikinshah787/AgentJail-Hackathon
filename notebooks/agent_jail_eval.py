import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import requests

    return mo, pd, requests


@app.cell
def _(mo):
    mo.md(r"""
    # AgentJail — Weave + live evaluation lab

    Judge console for **AgentJail**. This notebook talks to the live FastAPI API and pushes
    scored rows into **W&B Weave EvaluationLogger** (Evals tab), not just free-form traces.

    | Surface | URL |
    |---|---|
    | Product UI | http://127.0.0.1:5173/ariai-logic |
    | Weave traces | https://wandb.ai/rshah88-arizona-state-university/agent-jail/weave/traces |
    | Weave evals | https://wandb.ai/rshah88-arizona-state-university/agent-jail/weave/evaluations |

    **Honest scope:** controlled simulation + independent mock executor ledger. Does not claim production security.
    """)
    return


@app.cell
def _(mo):
    api_base = mo.ui.text(value="http://127.0.0.1:8000", label="AgentJail API")
    include_injec = mo.ui.checkbox(label="Include InjecAgent holdout in Weave eval", value=True)
    run_summary = mo.ui.run_button(label="1) Load live summary + probes", kind="neutral")
    run_weave = mo.ui.run_button(label="2) Run Weave EvaluationLogger suite", kind="success")
    mo.vstack([api_base, include_injec, run_summary, run_weave])
    return api_base, include_injec, run_summary, run_weave


@app.cell
def _(api_base, include_injec, requests, run_summary, run_weave):
    base = api_base.value.rstrip("/")
    connection_message = "Click a run button."
    weave_status = {"weave_enabled": False}
    summary = {}
    weave_run = {}
    demo_events = []

    try:
        health = requests.get(f"{base}/api/health", timeout=8)
        health.raise_for_status()
        weave_status = requests.get(f"{base}/api/v1/weave/status", timeout=8).json()
        connection_message = f"API healthy at {base}."
    except requests.RequestException as error:
        connection_message = f"Could not reach AgentJail API: {error}"

    if run_summary.value:
        try:
            summary = requests.get(f"{base}/api/v1/evaluations/summary", timeout=120).json()
            # Also run legacy-friendly demo trail for the scar story
            for scenario in [
                "protected_poisoned_ticket",
                "mutated_replay",
                "legitimate_sensitive_request",
            ]:
                event = requests.post(
                    f"{base}/api/v1/demo/run",
                    json={"scenario": scenario},
                    timeout=30,
                ).json()
                decision = event.get("decision") or {}
                if isinstance(decision, dict):
                    demo_events.append(
                        {
                            "scenario": scenario,
                            "decision": decision.get("decision"),
                            "executed": decision.get("executed"),
                            "reason": (decision.get("reason") or "")[:120],
                        }
                    )
                else:
                    demo_events.append({"scenario": scenario, "raw": str(event)[:120]})
            connection_message = f"Loaded summary + demos from {base}."
        except requests.RequestException as error:
            connection_message = f"Summary failed: {error}"

    if run_weave.value:
        try:
            weave_run = requests.post(
                f"{base}/api/v1/evaluations/weave-run",
                params={"include_injec": str(include_injec.value).lower()},
                timeout=300,
            ).json()
            connection_message = (
                f"Weave eval finished: {weave_run.get('passed_tests')}/{weave_run.get('total_tests')} "
                f"(pass_rate={weave_run.get('pass_rate')})."
            )
        except requests.RequestException as error:
            connection_message = f"Weave eval failed: {error}"
    return connection_message, demo_events, summary, weave_run, weave_status


@app.cell
def _(
    connection_message,
    demo_events,
    mo,
    pd,
    summary,
    weave_run,
    weave_status,
):
    weave_on = bool(weave_status.get("weave_enabled"))
    probes = summary.get("independent_probes") or {}
    injec = summary.get("injecagent_holdout") or {}

    status_rows = pd.DataFrame(
        [
            {"metric": "API", "value": connection_message},
            {
                "metric": "W&B Weave tracing",
                "value": "ON" if weave_on else "OFF — set WANDB_API_KEY",
            },
            {"metric": "Weave project", "value": weave_status.get("weave_project", "—")},
            {
                "metric": "Independent probes",
                "value": f"{probes.get('passed', '—')}/{probes.get('total', '—')}"
                if probes
                else "run summary",
            },
            {
                "metric": "Containment rate",
                "value": summary.get("containment_rate", "—"),
            },
            {
                "metric": "Benign utility",
                "value": summary.get("benign_utility", "—"),
            },
            {
                "metric": "InjecAgent holdout exec %",
                "value": (
                    f"{injec.get('unprotected_execution_rate')}% → {injec.get('agentjail_execution_rate')}%"
                    if injec.get("available")
                    else "—"
                ),
            },
            {
                "metric": "Last Weave EvaluationLogger",
                "value": (
                    f"{weave_run.get('name')} · {weave_run.get('passed_tests')}/{weave_run.get('total_tests')}"
                    if weave_run.get("ok")
                    else (weave_run.get("error") or "not run yet")
                ),
            },
        ]
    )

    claims = summary.get("honest_claims") or []
    if weave_run.get("honest_claim"):
        claims = [weave_run["honest_claim"], *claims]

    demo_df = (
        pd.DataFrame(demo_events)
        if demo_events
        else pd.DataFrame(columns=["scenario", "decision", "executed", "reason"])
    )
    fail_df = pd.DataFrame(weave_run.get("failures") or summary.get("failures") or [])

    links = mo.md(
        f"""
    ### Open for judges
    - [Weave traces]({weave_status.get('weave_traces_url') or 'https://wandb.ai/rshah88-arizona-state-university/agent-jail/weave/traces'})
    - [Weave evaluations]({weave_run.get('weave_evals_url') or 'https://wandb.ai/rshah88-arizona-state-university/agent-jail/weave/evaluations'})
    - [Product Control Room](http://127.0.0.1:5173/ariai-logic)
    """
    )

    claim_md = "\n".join(f"- {c}" for c in claims[:6]) or "_Run summary / Weave eval to populate claims._"
    dont = summary.get("do_not_claim") or weave_run.get("do_not_claim") or [
        "AgentJail prevents all prompt injection.",
        "AgentJail is production secure.",
        "These probes prove real-world security.",
    ]
    dont_md = "\n".join(f"- {c}" for c in dont)

    mo.vstack(
        [
            mo.callout(connection_message, kind="success" if weave_on else "warn"),
            links,
            mo.md("## Live metrics"),
            mo.ui.table(status_rows),
            mo.md("## Demo trail (v1 scenarios)"),
            mo.ui.table(demo_df),
            mo.md("## Honest claims"),
            mo.md(claim_md),
            mo.md("## Do not claim"),
            mo.md(dont_md),
            mo.md("## Failures (never hidden)"),
            mo.ui.table(fail_df if not fail_df.empty else pd.DataFrame([{"info": "none"}])),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
