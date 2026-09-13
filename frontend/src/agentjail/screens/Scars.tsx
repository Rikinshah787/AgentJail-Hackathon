import { useEffect, useState } from 'react'
import { fetchScars, useResource } from '../api'
import type { Scar } from '../types'
import { AlertBanner, DemoDataChip, StatusChip } from '../components/DecisionBadge'
import { Button, Card, EmptyState, ErrorState, LoadingState, SectionTitle } from '../components/ui'

export function Scars() {
  const { loading, error, data, source, reload } = useResource(fetchScars)
  const [items, setItems] = useState<Scar[]>([])

  useEffect(() => {
    if (data) setItems(data)
  }, [data])

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Known attack patterns"
        subtitle="Confirmed attacks that AgentJail can recognize if they return."
        action={source === 'demo' && !loading ? <DemoDataChip /> : null}
      />

      <AlertBanner tone="info">
        Scars are supporting evidence. Deterministic policy makes the final authorization decision.
      </AlertBanner>

      {loading ? <LoadingState label="Loading scars" /> : null}
      {error ? (
        <ErrorState title="Could not load scars" message={error.message} details={error.details} onRetry={reload} />
      ) : null}

      {!loading && !error && items.length === 0 ? (
        <EmptyState
          title="No scars yet"
          subtitle="When AgentJail confirms an attack, a scoped scar can remember the pattern."
        />
      ) : null}

      {!loading && !error ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {items.map((scar) => (
            <ScarCard
              key={scar.id}
              scar={scar}
              onDeactivate={() =>
                setItems((prev) => prev.map((s) => (s.id === scar.id ? { ...s, status: 'Expired' } : s)))
              }
            />
          ))}
        </div>
      ) : null}
    </div>
  )
}

function ScarCard({ scar, onDeactivate }: { scar: Scar; onDeactivate: () => void }) {
  const tone = scar.status === 'Active' ? 'allow' : scar.status === 'Under review' ? 'approve' : 'neutral'

  return (
    <Card hover className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs uppercase tracking-wide text-aj-muted">Example</p>
          <h3 className="mt-1 font-display text-xl font-bold">{scar.name}</h3>
        </div>
        <StatusChip tone={tone}>{scar.status}</StatusChip>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <Meta label="Tools affected" value={scar.tools.join(', ') || '—'} />
        <Meta label="Sources affected" value={scar.sources.join(', ') || '—'} />
        <Meta label="Times matched" value={String(scar.timesMatched)} />
        <Meta label="Created" value={scar.created} />
        <Meta label="Last matched" value={scar.lastMatched} />
        <Meta label="Reviewer" value={scar.reviewer} />
        <Meta label="Expiration" value={scar.expires} />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Button size="sm" variant="secondary">
          View matches
        </Button>
        <Button size="sm" variant="secondary">
          Edit scope
        </Button>
        <Button size="sm" variant="ghost" onClick={onDeactivate} disabled={scar.status === 'Expired'}>
          Deactivate
        </Button>
        <Button size="sm" variant="approve">
          Require approval instead of blocking
        </Button>
      </div>
    </Card>
  )
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-aj-border bg-aj-panel/50 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-aj-muted">{label}</p>
      <p className="mt-1 text-sm">{value}</p>
    </div>
  )
}
