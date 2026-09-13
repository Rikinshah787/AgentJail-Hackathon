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
import { AlertTriangle, FlaskConical, Gauge, Percent, ShieldCheck, Timer } from 'lucide-react'
import { fetchEvaluations, useResource } from '../api'
import { Button, Card, ErrorState, LoadingState, MetricCard, SectionTitle } from '../components/ui'
import { AlertBanner, DemoDataChip } from '../components/DecisionBadge'

export function Evaluations() {
  const { loading, error, data, source, reload } = useResource(fetchEvaluations)
  const chartData =
    data?.modes.map((m) => ({
      name: m.name.replace('AgentJail ', 'AJ '),
      'Attack success %': m.attackSuccess,
      'Legitimate completion %': m.taskCompletion,
    })) ?? []

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Does AgentJail stop attacks without breaking useful work?"
        subtitle="Probe data tests a real mechanism against an independent executor ledger — not AgentJail grading itself."
        action={source === 'demo' && !loading ? <DemoDataChip /> : null}
      />

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
                  {data.methodology ? <p className="mt-2 text-xs text-aj-muted">{data.methodology}</p> : null}
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
              <p className="mt-1 text-sm text-aj-muted">Failed runs are never hidden from this screen.</p>
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
            <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
              <div>
                <h3 className="font-display text-lg font-bold">Comparison modes</h3>
                <p className="text-sm text-aj-muted">
                  Attack success — lower is better · Legitimate completion — higher is better. Only rows marked measured
                  are from this build&apos;s ledger.
                </p>
              </div>
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
            <ul className="mt-4 space-y-1.5 text-xs text-aj-muted">
              {data.modes.map((m) => (
                <li key={m.name}>
                  <span className="font-semibold text-aj-text">{m.name}</span>
                  {m.measured ? ' · measured' : ' · illustrative'}
                  {m.note ? ` — ${m.note}` : ''}
                </li>
              ))}
            </ul>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard icon={FlaskConical} label="Attacks contained" value={`${data.attacksContained}%`} tone="allow" />
            <MetricCard icon={Percent} label="False-positive rate" value={`${data.falsePositiveRate}%`} tone="approve" />
            <MetricCard icon={Gauge} label="Approval rate" value={`${data.approvalRate}%`} tone="brand" />
            <MetricCard icon={Timer} label="p95 decision latency" value={`${data.p95LatencyMs}ms`} tone="brand" />
          </div>

          {data.injecHoldoutClaim || data.injecUnprotectedRate != null ? (
            <Card className="p-5">
              <h3 className="font-display text-lg font-bold">InjecAgent holdout (mapped)</h3>
              <p className="mt-2 text-sm text-aj-muted">
                Unprotected mock execution {data.injecUnprotectedRate ?? '—'}% → AgentJail{' '}
                {data.injecJailRate ?? '—'}% (independent ledger).
              </p>
              {data.injecHoldoutClaim ? (
                <p className="mt-3 text-sm leading-relaxed text-aj-text">{data.injecHoldoutClaim}</p>
              ) : null}
            </Card>
          ) : null}

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

          {data.doNotClaim.length ? (
            <Card className="border-aj-block/25 p-5">
              <h3 className="font-display text-lg font-bold text-aj-block">Do not claim</h3>
              <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-aj-muted">
                {data.doNotClaim.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </Card>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-3">
            <Card className="p-4">
              <p className="text-sm text-aj-muted">Scar match rate</p>
              <p className="mt-1 font-display text-2xl font-bold">{data.scarRecall}%</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-aj-muted">Decision cases completed</p>
              <p className="mt-1 font-display text-2xl font-bold">{data.casesCompleted}</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-aj-muted">Decision harness failures</p>
              <p className="mt-1 font-display text-2xl font-bold text-aj-block">{data.failures}</p>
            </Card>
          </div>
        </>
      ) : null}
    </div>
  )
}
