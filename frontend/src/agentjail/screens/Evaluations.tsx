import { useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AlertTriangle, ExternalLink, FlaskConical, Gauge, Percent, ShieldCheck, Timer } from 'lucide-react'
import { ApiError, fetchEvaluations, runGodVsJailEvaluation, useResource } from '../api'
import { Button, Card, ErrorState, LoadingState, MetricCard, SectionTitle } from '../components/ui'
import { AlertBanner, DemoDataChip } from '../components/DecisionBadge'

const WEAVE_EVALS = 'https://wandb.ai/rshah88-arizona-state-university/agent-jail/weave/evaluations'

export function Evaluations() {
  const { loading, error, data, source, reload } = useResource(fetchEvaluations)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [comparison, setComparison] = useState<Record<string, unknown> | null>(null)
  const chartData =
    data?.modes.map((m) => ({
      name: m.name.replace('AgentJail ', 'AJ '),
      'Attack success %': m.attackSuccess,
      'Legitimate completion %': m.taskCompletion,
    })) ?? []

  async function onGodVsJail() {
    setBusy(true)
    setErr(null)
    setMsg(null)
    try {
      const res = await runGodVsJailEvaluation()
      const body = res.data
      setComparison((body.comparison as Record<string, unknown>) || null)
      setMsg(String(body.honest_claim || body.submission_line || 'Published to Weave Evals.'))
      reload()
    } catch (e) {
      setErr(e instanceof ApiError ? e.details : e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Does AgentJail stop attacks without breaking useful work?"
        subtitle="Headline proof: same attack — no gate breaches, AgentJail blocks, scar blocks the paraphrase."
        action={source === 'demo' && !loading ? <DemoDataChip /> : null}
      />

      <Card className="border-aj-brand/30 bg-aj-brand/[0.07] p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-aj-brand">
              Headline · God agent vs AgentJail
            </p>
            <h3 className="mt-2 font-display text-xl font-bold">Same poisoned ticket · three labelled versions</h3>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-aj-muted">
              <code className="text-aj-text">no_guard</code> breaches · <code className="text-aj-text">agentjail</code>{' '}
              blocks · <code className="text-aj-text">agentjail+scar</code> blocks GLM paraphrase · legitimate restart
              still allowed. Scores: critical_breach, safe_action_allowed, scar_match, false_allow, latency.
            </p>
            {msg ? <p className="mt-3 text-sm text-aj-allow">{msg}</p> : null}
            {err ? (
              <p className="mt-3 text-sm text-aj-block" role="alert">
                {err}
              </p>
            ) : null}
            {comparison ? (
              <pre className="mt-3 max-h-40 overflow-auto rounded-xl border border-aj-border bg-aj-bg/80 p-3 text-xs text-aj-muted">
                {JSON.stringify(comparison, null, 2)}
              </pre>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" disabled={busy} onClick={() => void onGodVsJail()}>
              {busy ? 'Scoring in Weave…' : 'Run God vs AgentJail'}
            </Button>
            <a
              href={WEAVE_EVALS}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-xl border border-aj-border bg-aj-card px-3 py-2 text-sm font-medium text-aj-text hover:border-aj-brand/40"
            >
              Open Weave Evals <ExternalLink className="size-3.5" />
            </a>
          </div>
        </div>
      </Card>

      {loading ? <LoadingState label="Loading evaluations" /> : null}
      {error ? (
        <ErrorState
          title="Could not load evaluations"
          message={error.message}
          details={error.details}
          onRetry={reload}
        />
      ) : null}

      {!loading && !error && data ? (
        <>
          <AlertBanner tone="info">
            Probe or simulated data proves the mechanism works under controlled conditions. It does not prove AgentJail
            is secure in the real world.
          </AlertBanner>

          {typeof data.probeTotal === 'number' && data.probeTotal > 0 ? (
            <Card className="border-aj-brand/30 bg-aj-brand/[0.07] p-5">
              <div className="flex flex-wrap items-start gap-3">
                <ShieldCheck className="mt-0.5 size-5 text-aj-brand" aria-hidden />
                <div className="min-w-0 flex-1">
                  <h3 className="font-display text-lg font-bold">Independent observer probes</h3>
                  <p className="mt-1 text-sm text-aj-muted">
                    {data.probePassed}/{data.probeTotal} passed — deny means zero mock-server requests; allow means
                    exactly one request and a visible state change.
                  </p>
                </div>
              </div>
            </Card>
          ) : null}

          {data.failures > 0 ? (
            <Card className="border-aj-block/40 bg-aj-block/10 p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3 text-aj-block">
                  <AlertTriangle className="size-6" aria-hidden />
                  <div>
                    <p className="font-display text-xl font-bold">
                      {data.failures} evaluation errors need attention
                    </p>
                    <p className="text-sm text-aj-muted">Failed runs are never hidden from this screen.</p>
                  </div>
                </div>
                <Button variant="danger" size="sm" onClick={reload}>
                  Re-run
                </Button>
              </div>
            </Card>
          ) : (
            <Card className="border-aj-allow/35 bg-aj-allow/10 p-5">
              <p className="font-display text-lg font-bold text-aj-allow">No decision-harness failures in this run</p>
            </Card>
          )}

          <div className="flex flex-wrap gap-2">
            {data.benchmarks.map((b) => (
              <span
                key={b}
                className="rounded-full border border-aj-border bg-aj-panel px-3 py-1 text-xs font-medium text-aj-muted"
              >
                {b}
              </span>
            ))}
          </div>

          <Card className="p-5">
            <div className="mb-4">
              <h3 className="font-display text-lg font-bold">Comparison modes</h3>
              <p className="text-sm text-aj-muted">
                Attack success — lower is better · Legitimate completion — higher is better
              </p>
            </div>
            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e2a44" />
                  <XAxis dataKey="name" stroke="#8b9bb8" tick={{ fill: '#8b9bb8', fontSize: 12 }} />
                  <YAxis stroke="#8b9bb8" tick={{ fill: '#8b9bb8', fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      background: '#121a2e',
                      border: '1px solid #1e2a44',
                      borderRadius: 12,
                      color: '#f4f7ff',
                    }}
                  />
                  <Legend />
                  <Bar dataKey="Attack success %" fill="#ef4444" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="Legitimate completion %" fill="#22c55e" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard icon={FlaskConical} label="Attacks contained" value={`${data.attacksContained}%`} tone="allow" />
            <MetricCard icon={Percent} label="False-positive rate" value={`${data.falsePositiveRate}%`} tone="approve" />
            <MetricCard icon={Gauge} label="Approval rate" value={`${data.approvalRate}%`} tone="brand" />
            <MetricCard icon={Timer} label="p95 decision latency" value={`${data.p95LatencyMs}ms`} tone="brand" />
          </div>

          {data.honestClaims.length ? (
            <Card className="p-5">
              <h3 className="font-display text-lg font-bold">Claims you can honestly make</h3>
              <ul className="mt-3 space-y-2 text-sm leading-relaxed text-aj-text">
                {data.honestClaims.map((claim) => (
                  <li key={claim.slice(0, 48)} className="rounded-xl border border-aj-allow/25 bg-aj-allow/10 px-3 py-2">
                    {claim}
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}
        </>
      ) : null}
    </div>
  )
}
