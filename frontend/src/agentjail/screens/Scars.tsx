import { useEffect, useState } from 'react'
import {
  approveImprovementRun,
  fetchImprovementRuns,
  fetchScars,
  monitorImprovementRun,
  setScarActive,
  startImprovementRun,
  useResource,
} from '../api'
import type { ImprovementRun, Scar } from '../types'
import { AlertBanner, DemoDataChip, StatusChip } from '../components/DecisionBadge'
import { Button, Card, EmptyState, ErrorState, LoadingState, SectionTitle } from '../components/ui'

export function Scars() {
  const scars = useResource(fetchScars)
  const runs = useResource(fetchImprovementRuns)
  const [items, setItems] = useState<Scar[]>([])
  const [latest, setLatest] = useState<ImprovementRun | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [reviewer, setReviewer] = useState('security-on-call')
  const [reviewReason, setReviewReason] = useState('Attack and legitimate holdout thresholds passed.')

  useEffect(() => {
    if (scars.data) setItems(scars.data)
  }, [scars.data])

  useEffect(() => {
    if (runs.data?.length) setLatest(runs.data[0])
  }, [runs.data])

  async function perform(action: () => Promise<ImprovementRun>) {
    setBusy(true)
    setMessage('')
    try {
      const result = await action()
      setLatest(result)
      await Promise.all([scars.reload(), runs.reload()])
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Security memory and improvement loop"
        subtitle="Generate attacks, judge a narrow scar against attack and legitimate holdouts, approve it, then monitor for regressions."
        action={scars.source === 'demo' && !scars.loading ? <DemoDataChip /> : null}
      />

      <AlertBanner tone="info">
        Generation and evaluation are automatic and bounded. Activation remains a human decision; monitoring can
        automatically quarantine a regressing scar.
      </AlertBanner>

      <Card className="border-aj-brand/35 bg-aj-brand/[0.07] p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-aj-brand">Self-improvement controller</p>
            <h3 className="mt-1 font-display text-xl font-bold">
              {latest ? `Run ${latest.id} · ${latest.status.replaceAll('_', ' ')}` : 'No improvement run yet'}
            </h3>
            <p className="mt-2 text-sm text-aj-muted">
              Hard stop: 5 attempts · attack containment 100% · scar recall ≥80% · legitimate utility 100% · false
              positives 0%.
            </p>
          </div>
          <Button disabled={busy} onClick={() => void perform(() => startImprovementRun())}>
            {busy ? 'Working…' : 'Run improvement cycle'}
          </Button>
        </div>

        {latest ? <RunEvidence run={latest} /> : null}

        {latest?.status === 'awaiting_human' ? (
          <div className="mt-4 grid gap-3 rounded-xl border border-aj-approve/35 bg-aj-approve/10 p-4 md:grid-cols-2">
            <label className="text-sm text-aj-muted">
              Reviewer
              <input
                className="mt-1 w-full rounded-lg border border-aj-border bg-aj-bg px-3 py-2 text-aj-text"
                value={reviewer}
                onChange={(event) => setReviewer(event.target.value)}
              />
            </label>
            <label className="text-sm text-aj-muted">
              Review reason
              <input
                className="mt-1 w-full rounded-lg border border-aj-border bg-aj-bg px-3 py-2 text-aj-text"
                value={reviewReason}
                onChange={(event) => setReviewReason(event.target.value)}
              />
            </label>
            <Button
              variant="approve"
              disabled={busy || !reviewer.trim() || !reviewReason.trim()}
              onClick={() => void perform(() => approveImprovementRun(latest.id, reviewer, reviewReason))}
            >
              Human approve and activate
            </Button>
          </div>
        ) : null}

        {latest?.status === 'active' ? (
          <div className="mt-4">
            <Button variant="secondary" disabled={busy} onClick={() => void perform(() => monitorImprovementRun(latest.id))}>
              Run regression monitor
            </Button>
          </div>
        ) : null}
        {message ? <p className="mt-3 text-sm text-aj-block">{message}</p> : null}
      </Card>

      {scars.loading ? <LoadingState label="Loading scars" /> : null}
      {scars.error ? (
        <ErrorState title="Could not load scars" message={scars.error.message} details={scars.error.details} onRetry={scars.reload} />
      ) : null}
      {!scars.loading && !scars.error && items.length === 0 ? (
        <EmptyState title="No scars yet" subtitle="Run the improvement cycle to generate and evaluate a candidate." />
      ) : null}
      {!scars.loading && !scars.error ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {items.map((scar) => (
            <ScarCard
              key={scar.id}
              scar={scar}
              onStatus={async (active) => {
                await setScarActive(scar.id, active)
                await scars.reload()
              }}
            />
          ))}
        </div>
      ) : null}
    </div>
  )
}

function RunEvidence({ run }: { run: ImprovementRun }) {
  const metrics = run.monitorMetrics && Object.keys(run.monitorMetrics).length ? run.monitorMetrics : run.metrics
  return (
    <div className="mt-4">
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
        <Meta label="Iterations" value={String(run.iterations)} />
        <Meta label="Attack blocked" value={percent(metrics.attack_block_rate)} />
        <Meta label="Scar recall" value={percent(metrics.scar_recall)} />
        <Meta label="Legitimate utility" value={percent(metrics.benign_allow_rate)} />
        <Meta label="False positives" value={percent(metrics.false_positive_rate)} />
      </div>
      <p className="mt-3 text-sm text-aj-muted">{run.stopReason}</p>
      {run.candidateScarId ? <p className="mt-1 font-mono text-xs text-aj-muted">Candidate: {run.candidateScarId}</p> : null}
    </div>
  )
}

function ScarCard({ scar, onStatus }: { scar: Scar; onStatus: (active: boolean) => Promise<void> }) {
  const tone = scar.status === 'Active' ? 'allow' : scar.status === 'Under review' ? 'approve' : 'neutral'
  return (
    <Card hover className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs uppercase tracking-wide text-aj-muted">Scoped memory</p>
          <h3 className="mt-1 font-display text-xl font-bold">{scar.name}</h3>
        </div>
        <StatusChip tone={tone}>{scar.status}</StatusChip>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <Meta label="Tools affected" value={scar.tools.join(', ') || '—'} />
        <Meta label="Sources affected" value={scar.sources.join(', ') || '—'} />
        <Meta label="Times matched" value={String(scar.timesMatched)} />
        <Meta label="Reviewer" value={scar.reviewer} />
        <Meta label="Last matched" value={scar.lastMatched} />
        <Meta label="Expiration" value={scar.expires} />
      </div>
      <div className="mt-4">
        <Button
          size="sm"
          variant={scar.status === 'Active' ? 'ghost' : 'approve'}
          onClick={() => void onStatus(scar.status !== 'Active')}
        >
          {scar.status === 'Active' ? 'Deactivate' : 'Activate manually'}
        </Button>
      </div>
    </Card>
  )
}

function percent(value: unknown): string {
  return typeof value === 'number' ? `${Math.round(value * 100)}%` : '—'
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-aj-border bg-aj-panel/50 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-aj-muted">{label}</p>
      <p className="mt-1 break-words text-sm">{value}</p>
    </div>
  )
}
