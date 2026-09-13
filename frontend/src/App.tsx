import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { BreachArena, type ArenaEvent } from './arena/BreachArena'
import './App.css'

const API = ''
const WEAVE_FALLBACK = 'https://wandb.ai/rshah88-arizona-state-university/agent-jail/weave'

type EvalReport = {
  headline: string
  total: number
  passed: number
  pass_rate: number
  denies: number
  allows: number
  approvals: number
  scar_hits: number
  false_allows: number
}

type InjecAgentReport = EvalReport & {
  mapped: number
  unmapped: number
  mapped_denies: number
  source: string
}

type AriaCoach = {
  summary: string
  dominant_fail_mode: string
  dominant_fail_mode_label?: string
  recommendations: string[]
  ask_aria_prompt: string
  weave_url: string
  weave_enabled: boolean
  weave_project: string
  api_key_ready?: boolean
  llm_enriched?: boolean
  aria_status?: string
  how_to_use_aria?: string[]
  lesson?: { title: string; body: string }[]
  aria_report?: {
    headline: string
    analysis: string
    god_vs_jail: string
    next_policy: string
    judge_takeaway: string
  }
  timeline?: {
    mode: string
    decision: string
    tool: string
    plain_english: string
    reason: string
  }[]
  session: {
    events: number
    god_breaches: number
    jail_denies: number
    scar_hits: number
    executed: number
  }
}

type WeaveRun = {
  ok: boolean
  total?: number
  passed?: number
  pass_rate?: number
  weave_evals_url?: string
  honest_claim?: string
  comparison?: Record<string, unknown>
  error?: string
}

function explainDecision(event: ArenaEvent | null): { title: string; body: string } {
  if (!event) {
    return {
      title: 'Waiting for a tool call',
      body: 'Press Act 1. An SRE agent will try create_service_identity. Without AgentJail the sandbox IAM changes — that is the breach.',
    }
  }
  if (event.mode === 'god' && event.executed) {
    return {
      title: 'No firewall → action executed',
      body: `The agent ran ${event.tool} with no provenance check. In the sandbox you should see temporary-ops-admin appear. In production this would be a real privilege escalation.`,
    }
  }
  if (event.matched_scar) {
    return {
      title: 'Scar memory blocked a repeat',
      body: `AgentJail recognized a previously learned attack pattern and denied ${event.tool} before execution. This is the product differentiator: policy + memory across sessions.`,
    }
  }
  if (event.decision === 'deny') {
    return {
      title: 'Provenance check failed → deny + scar',
      body: `${event.reason} A scar was stored so paraphrased follow-ups can be blocked without rewriting the rule by hand.`,
    }
  }
  if (event.decision === 'approval_required') {
    return {
      title: 'Human must decide',
      body: `${event.reason} Click Approve only if you accept the blast radius — AgentJail does not auto-run privileged IAM.`,
    }
  }
  if (event.decision === 'allow') {
    return {
      title: 'Least privilege allow',
      body: `${event.reason} The firewall is not a blanket block — verified low-risk restarts still run.`,
    }
  }
  return { title: 'Decision', body: event.reason }
}

export default function App() {
  const [event, setEvent] = useState<ArenaEvent | null>(null)
  const [cloud, setCloud] = useState<ArenaEvent['environment'] | null>(null)
  const [act, setAct] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [banner, setBanner] = useState('Runtime firewall for autonomous SRE agents')
  const [story, setStory] = useState(
    'AgentJail verifies who asked for each tool action, enforces least privilege, remembers attacks as scars, and blocks repeats before execution.',
  )
  const [evalReport, setEvalReport] = useState<EvalReport | null>(null)
  const [injecReport, setInjecReport] = useState<InjecAgentReport | null>(null)
  const [stats, setStats] = useState({ blocked: 0, allowed: 0, breaches: 0, scars: 0, approvals: 0 })
  const [candidateScar, setCandidateScar] = useState<number | null>(null)
  const [scarApproved, setScarApproved] = useState(false)
  const [weaveRun, setWeaveRun] = useState<WeaveRun | null>(null)
  const [weaveLoading, setWeaveLoading] = useState(false)
  const [aria, setAria] = useState<AriaCoach | null>(null)
  const [ariaLoading, setAriaLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  const applyEvent = useCallback((data: ArenaEvent) => {
    setEvent(data)
    setCloud(data.environment)
    setStats((s) => ({
      blocked: s.blocked + (data.decision === 'deny' ? 1 : 0),
      allowed: s.allowed + (data.mode === 'jail' && data.executed ? 1 : 0),
      breaches: s.breaches + (data.mode === 'god' && data.executed ? 1 : 0),
      scars: data.scars,
      approvals: s.approvals + (data.decision === 'approval_required' ? 1 : 0),
    }))
    if (data.candidate_scar_index != null) {
      setCandidateScar(data.candidate_scar_index)
      setScarApproved(false)
    }
  }, [])

  const askAria = useCallback(async () => {
    setAriaLoading(true)
    setError('')
    try {
      const response = await fetch(`${API}/api/aria/coach`, { method: 'POST' })
      if (!response.ok) throw new Error('ARIA coach unavailable — is the backend running?')
      setAria((await response.json()) as AriaCoach)
      setAct((prev) => Math.max(prev, 4))
      requestAnimationFrame(() => {
        document.getElementById('aria-lab')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ARIA coach failed')
    } finally {
      setAriaLoading(false)
    }
  }, [])

  const run = useCallback(
    async (scenario: string, mode: 'god' | 'jail', label: string, nextStory: string) => {
      setLoading(true)
      setError('')
      setBanner(label)
      setStory(nextStory)
      try {
        const response = await fetch(`${API}/api/demo/${scenario}?mode=${mode}`, { method: 'POST' })
        if (!response.ok) throw new Error('Backend not reachable')
        const data = (await response.json()) as ArenaEvent
        applyEvent(data)
        return data
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Request failed')
        return null
      } finally {
        setLoading(false)
      }
    },
    [applyEvent],
  )

  const resetAll = useCallback(async () => {
    setEvent(null)
    setCloud(null)
    setAct(0)
    setEvalReport(null)
    setInjecReport(null)
    setAria(null)
    setStats({ blocked: 0, allowed: 0, breaches: 0, scars: 0, approvals: 0 })
    setCandidateScar(null)
    setScarApproved(false)
    setWeaveRun(null)
    setBanner('Runtime firewall for autonomous SRE agents')
    setStory('Click ACT 1 — show what happens when an agent has no firewall.')
    await fetch(`${API}/api/reset`, { method: 'POST' }).catch(() => undefined)
  }, [])

  const act1 = useCallback(async () => {
    await fetch(`${API}/api/reset`, { method: 'POST' }).catch(() => undefined)
    setAria(null)
    setStats({ blocked: 0, allowed: 0, breaches: 0, scars: 0, approvals: 0 })
    setCandidateScar(null)
    setScarApproved(false)
    setAct(1)
    await run(
      'poisoned_alert',
      'god',
      'ACT 1 · WITHOUT AGENTJAIL — BREACH',
      'Poisoned incident ticket. Ungated agent creates cluster-admin. Watch IAM turn red.',
    )
  }, [run])

  const act2 = useCallback(async () => {
    await fetch(`${API}/api/reset?clear_session_log=false`, { method: 'POST' }).catch(() => undefined)
    setCloud(null)
    setAct(2)
    await run(
      'poisoned_alert',
      'jail',
      'ACT 2 · AGENTJAIL CONTAINS IT',
      'Same ticket. Unverified source → critical risk → BLOCKED. Scar written. No IAM mutation.',
    )
  }, [run])

  const act3 = useCallback(async () => {
    if (!scarApproved) {
      setError('Approve the candidate guardrail before replaying the mutated attack.')
      return
    }
    setAct(3)
    await run(
      'mutated_replay',
      'jail',
      'ACT 3 · SCAR STOPS THE MUTATION',
      'Paraphrased attack via agent-message. Scar matches → blocked again.',
    )
    await new Promise((r) => setTimeout(r, 900))
    await run(
      'safe_restart',
      'jail',
      'ACT 3 · LEGITIMATE WORK STILL RUNS',
      'Signed alert restarts gpu-worker-12. Least privilege — not a blanket deny.',
    )
    await askAria()
  }, [askAria, run, scarApproved])

  const playAll = useCallback(async () => {
    await act1()
    await new Promise((r) => setTimeout(r, 1600))
    await act2()
    setBanner('HUMAN REVIEW REQUIRED')
    setStory('The attack is contained. Approve the candidate guardrail, then run Act 3 to test it against GLM’s mutation.')
  }, [act1, act2])

  const approveScar = useCallback(async () => {
    if (candidateScar == null) return
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${API}/api/scars/${candidateScar}/activate`, { method: 'POST' })
      if (!response.ok) throw new Error('Candidate guardrail could not be activated')
      setScarApproved(true)
      setBanner('GUARDRAIL APPROVED · READY FOR ADVERSARIAL REPLAY')
      setStory('Human-reviewed scar is active. Run Act 3: GLM will change the wording while preserving the dangerous intent.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Guardrail approval failed')
    } finally {
      setLoading(false)
    }
  }, [candidateScar])

  const publishWeave = useCallback(async () => {
    setWeaveLoading(true)
    setError('')
    try {
      const response = await fetch(`${API}/api/v1/evaluations/god-vs-jail`, { method: 'POST' })
      const data = (await response.json()) as WeaveRun
      if (!response.ok || !data.ok) throw new Error(data.error || 'God vs AgentJail evaluation failed')
      setWeaveRun(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Weave evaluation failed')
    } finally {
      setWeaveLoading(false)
    }
  }, [])

  const runEval = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API}/api/eval`, { method: 'POST' })
      if (!response.ok) throw new Error('Eval failed')
      setEvalReport((await response.json()) as EvalReport)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Eval failed')
    } finally {
      setLoading(false)
    }
  }, [])

  const runInjecAgent = useCallback(async () => {
    setLoading(true)
    setError('')
    setBanner('INJECAGENT PUBLIC CORPUS')
    setStory(
      '1,054 public indirect-injection cases from InjecAgent, mapped onto Agent Jail tool calls. Privileged tools from unverified channels should deny; unmapped tools fail closed.',
    )
    try {
      const response = await fetch(`${API}/api/eval/injecagent`, { method: 'POST' })
      if (!response.ok) throw new Error('InjecAgent eval failed')
      setInjecReport((await response.json()) as InjecAgentReport)
      const play = await fetch(`${API}/api/eval/injecagent/play`, { method: 'POST' })
      if (!play.ok) throw new Error('InjecAgent play failed')
      applyEvent((await play.json()) as ArenaEvent)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'InjecAgent eval failed')
    } finally {
      setLoading(false)
    }
  }, [applyEvent])

  const playInjecReplay = useCallback(async () => {
    setLoading(true)
    setError('')
    setBanner('INJECAGENT SCAR REPLAY')
    setStory('Same public attacker tool, different injection channel. Scar memory should intercept it.')
    try {
      const play = await fetch(`${API}/api/eval/injecagent/play?replay=true`, { method: 'POST' })
      if (!play.ok) throw new Error('InjecAgent replay failed')
      applyEvent((await play.json()) as ArenaEvent)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'InjecAgent replay failed')
    } finally {
      setLoading(false)
    }
  }, [applyEvent])

  const approve = useCallback(async () => {
    if (!event?.pending_id) return
    setLoading(true)
    try {
      const response = await fetch(`${API}/api/approve/${event.pending_id}`, { method: 'POST' })
      if (!response.ok) throw new Error('Approve failed')
      applyEvent((await response.json()) as ArenaEvent)
      setBanner('OPERATOR APPROVED — privileged action executed')
      setStory('Human-in-the-loop: allow / deny / require_approval is a first-class outcome.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Approve failed')
    } finally {
      setLoading(false)
    }
  }, [applyEvent, event?.pending_id])

  const showApprovalCase = useCallback(async () => {
    setAct(4)
    await run(
      'verified_identity_approval',
      'jail',
      'BONUS · REQUIRE APPROVAL',
      'Verified source, privileged tool — not auto-allowed. Operator must approve.',
    )
  }, [run])

  const copyPrompt = useCallback(async () => {
    const text = aria?.ask_aria_prompt
    if (!text) return
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [aria?.ask_aria_prompt])

  const admin = cloud?.identities?.['temporary-ops-admin']
  const breached = Boolean(admin)
  const lesson = explainDecision(event)
  const weaveUrl = aria?.weave_url || WEAVE_FALLBACK
  const report = aria?.aria_report
  const ariaLive = Boolean(aria?.llm_enriched || aria?.api_key_ready)

  return (
    <main>
      <header>
        <div>
          <span className="eyebrow">RUNTIME FIREWALL FOR AUTONOMOUS AGENTS</span>
          <h1>
            AGENT <i>JAIL</i>
          </h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <Link
            to="/ariai-logic"
            className="aria-btn"
            style={{ textDecoration: 'none', whiteSpace: 'nowrap' }}
          >
            Open AgentJail Control Room
          </Link>
          <div className={`status ${breached ? 'deny' : event?.decision ?? 'idle'}`}>
            <span className="dot" />
            {breached
              ? 'BREACH — IAM MUTATED'
              : event?.decision === 'deny'
                ? 'BLOCKED BEFORE EXECUTION'
                : event?.decision === 'approval_required'
                  ? 'WAITING ON HUMAN'
                  : event?.decision === 'allow'
                    ? 'ALLOWED'
                    : 'ARMED'}
          </div>
        </div>
      </header>

      <p className="mission">{story}</p>

      <section className="steps">
        <button className="step bad" disabled={loading} onClick={() => void act1()}>
          <span>1</span>
          <div>
            <strong>Act 1 — Attack wins</strong>
            <small>No firewall → cluster-admin created</small>
          </div>
        </button>
        <button className="step good" disabled={loading} onClick={() => void act2()}>
          <span>2</span>
          <div>
            <strong>Act 2 — Jail blocks</strong>
            <small>Unverified source denied + scar</small>
          </div>
        </button>
        <button className="step mem" disabled={loading} onClick={() => void act3()}>
          <span>3</span>
          <div>
            <strong>Act 3 — Learns + allows legit</strong>
            <small>Scar replay + signed restart + ARIA</small>
          </div>
        </button>
        <button className="step reset" disabled={loading} onClick={() => void playAll()}>
          ▶ Play all
        </button>
      </section>

      <section className="flow">
        <span className={act >= 1 ? 'on danger' : ''}>01 ATTACK</span>
        <b>→</b>
        <span className={act >= 2 ? 'on' : ''}>02 CONTAIN</span>
        <b>→</b>
        <span className={act >= 3 ? 'on' : ''}>03 HARDEN</span>
        <b>→</b>
        <span
          className={act >= 4 || aria ? 'on' : ''}
          role="button"
          tabIndex={0}
          onClick={() => document.getElementById('aria-lab')?.scrollIntoView({ behavior: 'smooth' })}
          onKeyDown={(e) => {
            if (e.key === 'Enter') document.getElementById('aria-lab')?.scrollIntoView({ behavior: 'smooth' })
          }}
          style={{ cursor: 'pointer' }}
        >
          04 ARIA
        </span>
      </section>

      <section className="scoreboard">
        <b>
          {stats.blocked}
          <small>BLOCKED</small>
        </b>
        <b>
          {stats.allowed}
          <small>SAFE ALLOWED</small>
        </b>
        <b>
          {stats.scars}
          <small>SCARS</small>
        </b>
        <b>
          {stats.approvals}
          <small>NEED APPROVAL</small>
        </b>
        <b>
          &lt;1ms
          <small>GUARD LATENCY</small>
        </b>
      </section>

      {candidateScar != null && !scarApproved && (
        <section className="candidate-policy">
          <div>
            <span className="eyebrow">CANDIDATE GUARDRAIL · HUMAN REVIEW</span>
            <h2>Deny privileged identity creation from unverified sources</h2>
            <p>Generated from the contained attack. It remains inactive until an operator approves it.</p>
          </div>
          <button type="button" disabled={loading} onClick={() => void approveScar()}>
            Approve guardrail →
          </button>
        </section>
      )}

      {act >= 4 && aria && (
        <section className="weave-receipt">
          <div className="receipt-head">
            <div>
              <span className="eyebrow">W&B WEAVE · DECISION RECEIPT</span>
              <h2>The trajectory, not a screenshot</h2>
            </div>
            <button type="button" disabled={weaveLoading} onClick={() => void publishWeave()}>
              {weaveLoading
                ? 'Scoring God vs Jail…'
                : weaveRun?.ok
                  ? 'God vs Jail published ✓'
                  : 'Publish God vs Jail'}
            </button>
          </div>
          <div className="receipt-grid">
            <b>{stats.blocked}<small>ATTACKS BLOCKED</small></b>
            <b>{stats.allowed}<small>LEGITIMATE ALLOWED</small></b>
            <b>{Math.max(0, stats.breaches - 1)}<small>UNAUTHORIZED GUARDED EXECUTIONS</small></b>
            <b>{aria.session.events}<small>DECISIONS TRACED</small></b>
          </div>
          {weaveRun?.ok && (
            <a href={weaveRun.weave_evals_url || weaveUrl} target="_blank" rel="noreferrer">
              Open Weave Evals ↗
              {typeof weaveRun.passed === 'number' && typeof weaveRun.total === 'number'
                ? ` · ${weaveRun.passed}/${weaveRun.total} checks`
                : weaveRun.honest_claim
                  ? ` · ${weaveRun.honest_claim}`
                  : ''}
            </a>
          )}
        </section>
      )}

      <section className="explain-strip">
        <span className="eyebrow">WHAT JUST HAPPENED</span>
        <h2>{lesson.title}</h2>
        <p>{lesson.body}</p>
      </section>

      <section className="stage">
        <div className="arena">
          <BreachArena event={event} />
          {banner && (
            <div className={`cinematic ${breached ? 'deny' : event?.decision ?? 'idle'}`}>{banner}</div>
          )}
        </div>

        <aside className="cloud-panel">
          <span className="eyebrow">LIVE PROOF</span>
          <h2>{breached ? '⚠ Simulated IAM mutated' : 'Cloud sandbox snapshot'}</h2>
          <p className="reason">{event?.reason ?? 'Run Act 1 to see an ungated agent execute.'}</p>

          <div className={`cloud-card ${breached ? 'hot' : ''}`}>
            <h3>Identities</h3>
            {cloud?.identities ? (
              Object.entries(cloud.identities).map(([k, v]) => (
                <div key={k} className={k.includes('temporary') || String(v).includes('admin') ? 'row danger' : 'row'}>
                  <code>{k}</code>
                  <b>{v}</b>
                </div>
              ))
            ) : (
              <p className="empty">No snapshot yet.</p>
            )}
          </div>

          <div className="cloud-card">
            <h3>Workloads</h3>
            {cloud?.workloads ? (
              Object.entries(cloud.workloads).map(([k, v]) => (
                <div key={k} className="row">
                  <code>{k}</code>
                  <b>{v}</b>
                </div>
              ))
            ) : (
              <p className="empty">—</p>
            )}
          </div>

          {event?.attacker_proposal && (
            <div className="cloud-card attacker-card">
              <h3>GLM ATTACKER · STRUCTURED PROPOSAL</h3>
              <div className="row"><code>model</code><b>{event.attacker_proposal.model}</b></div>
              <div className="row"><code>source</code><b>{event.attacker_proposal.source}</b></div>
              <div className="row"><code>tool</code><b>{event.attacker_proposal.requested_tool}</b></div>
              <p className="aria-summary">{event.attacker_proposal.rationale}</p>
              <small>{event.attacker_proposal.model_powered ? 'LIVE W&B SERVERLESS INFERENCE' : 'DETERMINISTIC SAFE FALLBACK'}</small>
            </div>
          )}

          {event?.pending_id && (
            <div className="cloud-card aria-card">
              <h3>HUMAN APPROVAL</h3>
              <p className="aria-summary">{event.reason}</p>
              <button className="aria-btn" disabled={loading} onClick={() => void approve()}>
                Approve privileged action
              </button>
            </div>
          )}

          <div className="cloud-card">
            <h3>TOOLS</h3>
            <button className="aria-btn" disabled={loading} onClick={() => void showApprovalCase()}>
              Show require_approval case
            </button>
            <button className="aria-btn" disabled={loading} onClick={() => void runEval()} style={{ marginTop: 8 }}>
              Run adversarial eval suite
            </button>
            <button className="aria-btn" disabled={loading} onClick={() => void runInjecAgent()} style={{ marginTop: 8 }}>
              Run InjecAgent public corpus
            </button>
            <button className="aria-btn" disabled={loading} onClick={() => void playInjecReplay()} style={{ marginTop: 8 }}>
              Play InjecAgent scar replay
            </button>
            <button className="aria-btn" disabled={loading} onClick={() => void resetAll()} style={{ marginTop: 8 }}>
              Reset demo
            </button>
          </div>

          {evalReport && (
            <div className="cloud-card" style={{ borderColor: '#61f6cd' }}>
              <h3>EVAL EVIDENCE</h3>
              <p className="aria-summary">{evalReport.headline}</p>
              <div className="row">
                <code>pass_rate</code>
                <b>{(evalReport.pass_rate * 100).toFixed(0)}%</b>
              </div>
              <div className="row">
                <code>false_allows</code>
                <b>{evalReport.false_allows}</b>
              </div>
            </div>
          )}

          {injecReport && (
            <div className="cloud-card" style={{ borderColor: '#61f6cd' }}>
              <h3>INJECAGENT CORPUS</h3>
              <p className="aria-summary">{injecReport.headline}</p>
              <div className="row">
                <code>cases</code>
                <b>{injecReport.total}</b>
              </div>
              <div className="row">
                <code>mapped_denies</code>
                <b>{injecReport.mapped_denies}/{injecReport.mapped}</b>
              </div>
              <div className="row">
                <code>fail_closed</code>
                <b>{injecReport.unmapped}</b>
              </div>
              <div className="row">
                <code>false_allows</code>
                <b>{injecReport.false_allows}</b>
              </div>
              <div className="row">
                <code>scar_hits</code>
                <b>{injecReport.scar_hits}</b>
              </div>
            </div>
          )}
        </aside>
      </section>

      <section className="aria-lab" id="aria-lab">
        <div className="aria-lab-head">
          <div>
            <span className="eyebrow">ASK ARIA · LIVE IN THIS APP</span>
            <h2>Ask ARIA — judge report from your session</h2>
            <p>
              Your <code>WANDB_API_KEY</code> is already wired. Click Ask ARIA and W&amp;B Inference analyzes this
              demo session (God vs Jail, scars, next policy) right here. Weave stays optional for inspecting traces.
            </p>
          </div>
          <div className="aria-actions">
            <button className="primary" disabled={ariaLoading || loading} onClick={() => void askAria()}>
              {ariaLoading ? 'ARIA reading session…' : 'Ask ARIA'}
              <small>
                {aria?.api_key_ready === false
                  ? 'API key missing in backend/.env'
                  : 'Runs on W&B Inference with your key'}
              </small>
            </button>
            <a className="weave-btn" href={weaveUrl} target="_blank" rel="noreferrer">
              Open Weave traces
              <small>{aria?.weave_enabled ? 'Tracing ON' : 'Optional — inspect nested incidents'}</small>
            </a>
          </div>
        </div>

        <div className="aria-primer">
          <article>
            <h3>In-app Ask ARIA</h3>
            <p>
              Official ARIA lives in the W&amp;B UI (no public chat API). This coach uses the same API key +
              session/Weave context to produce the judge briefing inside the demo.
            </p>
          </article>
          <article>
            <h3>What it reads</h3>
            <p>
              Act 1–3 events: ungated breaches, Jail denies, scar hits, and allowed safe restarts — then names the
              dominant failure mode.
            </p>
          </article>
          <article>
            <h3>What judges should hear</h3>
            <p>
              Provenance gate + scar memory is the product. ARIA is the explanation layer that turns traces into the
              next self-improving experiment.
            </p>
          </article>
        </div>

        {!aria && (
          <div className="aria-empty tall">
            <p className="aria-empty-lead">
              Run <b>Play all</b> or <b>Act 1 → 2 → 3</b>, then click <b>Ask ARIA</b>. Act 3 auto-asks after the safe
              restart.
            </p>
            <ol>
              <li>
                <b>Act 1</b> — no firewall → IAM mutation.
              </li>
              <li>
                <b>Act 2</b> — Jail denies + writes a scar.
              </li>
              <li>
                <b>Act 3</b> — mutated replay blocked; signed restart allowed.
              </li>
              <li>
                <b>Ask ARIA</b> — live report appears below (not a copy-paste step).
              </li>
            </ol>
          </div>
        )}

        {aria && (
          <div className="aria-grid tall">
            <article className="aria-brief aria-report-card">
              <span className="eyebrow">{ariaLive && aria.llm_enriched ? 'ASK ARIA · LIVE' : 'ASK ARIA · REPORT'}</span>
              <h3>{report?.headline || aria.dominant_fail_mode_label || aria.dominant_fail_mode}</h3>
              <p className="aria-lead">{aria.summary}</p>
              {report?.analysis && <p>{report.analysis}</p>}
              <div className="aria-stats">
                <b>
                  {aria.session.god_breaches}
                  <small>GOD BREACHES</small>
                </b>
                <b>
                  {aria.session.jail_denies}
                  <small>JAIL DENIES</small>
                </b>
                <b>
                  {aria.session.scar_hits}
                  <small>SCAR HITS</small>
                </b>
                <b>
                  {aria.session.events}
                  <small>EVENTS</small>
                </b>
              </div>
              <p className="aria-meta">
                {aria.llm_enriched
                  ? `Live via W&B Inference · ${aria.weave_project}`
                  : aria.api_key_ready
                    ? `Structured report ready · status ${aria.aria_status || 'fallback'}`
                    : 'Add WANDB_API_KEY to backend/.env for live Ask ARIA'}
              </p>
              <h4>Recommendations</h4>
              <ul>
                {aria.recommendations.map((rec) => (
                  <li key={rec}>{rec}</li>
                ))}
              </ul>
            </article>

            <article className="aria-brief">
              <span className="eyebrow">GOD VS JAIL</span>
              <div className="lesson-block">
                <h4>Comparison</h4>
                <p>{report?.god_vs_jail || 'Run Ask ARIA after the three acts for the comparison.'}</p>
              </div>
              <div className="lesson-block">
                <h4>Next policy / scar</h4>
                <p>{report?.next_policy || aria.recommendations[0]}</p>
              </div>
              <div className="lesson-block">
                <h4>Judge takeaway</h4>
                <p>{report?.judge_takeaway || 'Provenance-aware authorization + scar memory.'}</p>
              </div>
              {(aria.lesson || []).slice(0, 2).map((item) => (
                <div key={item.title} className="lesson-block">
                  <h4>{item.title}</h4>
                  <p>{item.body}</p>
                </div>
              ))}
              <details className="aria-advanced">
                <summary>Optional: open same prompt in Weave UI</summary>
                <button type="button" className="aria-btn" onClick={() => void copyPrompt()}>
                  {copied ? 'Prompt copied' : 'Copy prompt'}
                </button>
                <pre className="aria-prompt">{aria.ask_aria_prompt}</pre>
              </details>
            </article>

            <article className="aria-brief">
              <span className="eyebrow">SESSION TIMELINE (PLAIN ENGLISH)</span>
              {(aria.timeline || []).length === 0 && <p className="empty">No events yet — run the acts first.</p>}
              <div className="timeline">
                {(aria.timeline || []).map((row, idx) => (
                  <div key={`${row.tool}-${idx}`} className={`tl ${row.decision}`}>
                    <span>
                      {row.mode.toUpperCase()} · {row.decision} · {row.tool}
                    </span>
                    <p>{row.plain_english}</p>
                  </div>
                ))}
              </div>
            </article>
          </div>
        )}
      </section>

      {error && (
        <p className="error">
          {error}. Use http://127.0.0.1:5173 — backend on 8000.
        </p>
      )}

      <footer>
        AgentJail = provenance-aware authorization + scar memory · sandbox cloud · Weave traces · ARIA explains the loop
      </footer>
    </main>
  )
}
