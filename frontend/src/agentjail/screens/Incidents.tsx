import { useEffect, useState } from 'react'
import { CheckCircle2, ExternalLink, RotateCcw, Shield } from 'lucide-react'
import { fetchIncidents, useResource } from '../api'
import { DecisionBadge, DemoDataChip, RiskChip, StatusChip } from '../components/DecisionBadge'
import { Button, Card, EmptyState, ErrorState, LoadingState, SectionTitle } from '../components/ui'
import { cn } from '../lib/utils'
import type { Incident } from '../types'

const TABS = ['Summary', 'Decision evidence', 'Trace', 'Raw event'] as const

export function Incidents() {
  const { loading, error, data, source, reload } = useResource(fetchIncidents)
  const incidents = data ?? []
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [tab, setTab] = useState<(typeof TABS)[number]>('Summary')
  const [reviewed, setReviewed] = useState(false)

  useEffect(() => {
    if (!selectedId && incidents[0]) setSelectedId(incidents[0].id)
  }, [incidents, selectedId])

  const incident = incidents.find((item) => item.id === selectedId) ?? incidents[0]

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Incidents"
        subtitle="A simple vertical timeline of what the agent tried and what AgentJail decided."
        action={source === 'demo' && !loading ? <DemoDataChip /> : null}
      />

      {loading ? <LoadingState label="Loading incidents" /> : null}
      {error ? (
        <ErrorState title="Could not load incidents" message={error.message} details={error.details} onRetry={reload} />
      ) : null}

      {!loading && !error && incidents.length === 0 ? (
        <EmptyState
          title="No incidents yet"
          subtitle="Run a scenario in Live Demo. AgentJail will record what the agent tried and what it decided."
        />
      ) : null}

      {!loading && !error && incidents.length > 1 ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {incidents.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                setSelectedId(item.id)
                setTab('Summary')
                setReviewed(false)
              }}
              className={cn(
                'rounded-2xl border p-4 text-left transition',
                item.id === incident?.id
                  ? 'border-aj-brand bg-aj-brand/15'
                  : 'border-aj-border bg-aj-card/70 hover:border-aj-brand/40',
              )}
            >
              <div className="flex flex-wrap items-center gap-2">
                <DecisionBadge decision={item.decision} size="sm" />
                <RiskChip risk={item.risk} />
              </div>
              <p className="mt-3 font-display text-base font-bold leading-snug">{item.title}</p>
              <p className="mt-1 text-xs text-aj-muted">{item.summary}</p>
            </button>
          ))}
        </div>
      ) : null}

      {incident && !loading && !error ? <IncidentDetail incident={incident} tab={tab} setTab={setTab} reviewed={reviewed} setReviewed={setReviewed} /> : null}
    </div>
  )
}

function IncidentDetail({
  incident,
  tab,
  setTab,
  reviewed,
  setReviewed,
}: {
  incident: Incident
  tab: (typeof TABS)[number]
  setTab: (tab: (typeof TABS)[number]) => void
  reviewed: boolean
  setReviewed: (v: boolean) => void
}) {
  return (
    <div className="space-y-6">
      <SectionTitle title={incident.title} />

      <Card
        className={cn(
          'p-6',
          incident.executed ? 'border-aj-approve/35 bg-aj-approve/[0.08]' : 'border-aj-allow/35 bg-aj-allow/[0.08]',
        )}
      >
        <p
          className={cn(
            'font-display text-2xl font-bold tracking-tight',
            incident.executed ? 'text-aj-approve' : 'text-aj-allow',
          )}
        >
          {incident.summary}
        </p>
        <p className="mt-1.5 text-sm text-aj-muted">The most important fact for responders and judges.</p>
      </Card>

      <div className="flex flex-wrap gap-2">
        <DecisionBadge decision={incident.decision} />
        <RiskChip risk={incident.risk} />
        <StatusChip tone={incident.executed ? 'approve' : 'allow'}>
          <CheckCircle2 className="size-3.5" aria-hidden />
          {incident.executed ? 'Simulated action ran' : 'No action executed'}
        </StatusChip>
        {reviewed ? <StatusChip tone="brand">Reviewed</StatusChip> : null}
      </div>

      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" size="sm">
          <RotateCcw className="size-3.5" /> Replay incident
        </Button>
        <Button variant="secondary" size="sm">
          Update policy
        </Button>
        <Button variant="secondary" size="sm" onClick={() => setReviewed(true)}>
          Mark as reviewed
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() =>
            window.open(
              'https://wandb.ai/rshah88-arizona-state-university/agent-jail/weave/traces?view=traces_default',
              '_blank',
              'noopener,noreferrer',
            )
          }
        >
          <ExternalLink className="size-3.5" /> Open in Weave
        </Button>
      </div>

      <div className="flex flex-wrap gap-1 rounded-xl border border-aj-border bg-aj-panel p-1">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={cn(
              'rounded-lg px-3 py-2 text-sm font-medium transition',
              tab === t ? 'bg-aj-brand/20 text-aj-text' : 'text-aj-muted hover:text-aj-text',
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'Summary' ? (
        <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <Card className="p-6">
            <ol className="relative space-y-6 border-l border-aj-border pl-6">
              {incident.timeline.map((step, i) => (
                <li key={`${step.title}-${i}`} className="relative">
                  <span className="absolute -left-[1.9rem] flex size-6 items-center justify-center rounded-full border border-aj-brand/40 bg-aj-panel text-xs font-bold text-aj-brand">
                    {i + 1}
                  </span>
                  <p className="font-semibold">{step.title}</p>
                  <p className="mt-1 text-sm text-aj-muted">{step.detail}</p>
                  {step.checks ? (
                    <ul className="mt-3 space-y-1.5">
                      {step.checks.map((c) => (
                        <li
                          key={c.label}
                          className="flex items-center justify-between gap-3 rounded-lg border border-aj-border bg-aj-panel/70 px-3 py-2 text-sm"
                        >
                          <span>{c.label}</span>
                          <span className={c.ok === false ? 'font-medium text-aj-block' : 'text-aj-muted'}>
                            {c.value}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </li>
              ))}
            </ol>
          </Card>

          <Card className="space-y-4 p-6">
            <p className="font-display text-lg font-bold">Answer these five questions</p>
            {[
              ['What did the agent try to do?', incident.whatTried],
              ['Why was it risky?', incident.whyRisky],
              ['What did AgentJail decide?', incident.whatDecided],
              ['Did anything actually happen?', incident.whatHappened],
              ['What should the human do next?', incident.nextStep],
            ].map(([q, a]) => (
              <div key={q}>
                <p className="text-xs font-semibold uppercase tracking-wide text-aj-brand">{q}</p>
                <p className="mt-1 text-sm text-aj-muted">{a}</p>
              </div>
            ))}
          </Card>
        </div>
      ) : null}

      {tab === 'Decision evidence' ? (
        <Card className="p-6">
          <div className="flex items-center gap-2 text-aj-brand">
            <Shield className="size-5" aria-hidden />
            <h3 className="font-display text-xl font-bold">Decision evidence</h3>
          </div>
          <ul className="mt-4 space-y-2 text-sm text-aj-muted">
            {incident.timeline
              .flatMap((step) => step.checks ?? [])
              .map((check) => (
                <li key={check.label}>
                  {check.label}: {check.value}
                </li>
              ))}
            {!incident.timeline.some((step) => step.checks?.length) ? (
              <>
                <li>{incident.whyRisky}</li>
                <li>{incident.whatDecided}</li>
                <li>{incident.whatHappened}</li>
              </>
            ) : null}
          </ul>
        </Card>
      ) : null}

      {tab === 'Trace' ? (
        <Card className="p-6 font-mono text-sm text-aj-muted">
          <p>trace_id: {incident.technical.traceId}</p>
          <p>latency_ms: {incident.technical.latencyMs}</p>
          <p>policy_id: {incident.technical.policyId}</p>
          <p>risk_score: {incident.technical.riskScore}</p>
          <p>actor_id: {incident.technical.actorId}</p>
        </Card>
      ) : null}

      {tab === 'Raw event' ? (
        <Card className="overflow-x-auto p-6">
          <pre className="text-xs leading-relaxed text-aj-muted">{JSON.stringify(incident.technical, null, 2)}</pre>
        </Card>
      ) : null}
    </div>
  )
}
