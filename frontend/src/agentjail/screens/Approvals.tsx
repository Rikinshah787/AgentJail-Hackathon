import { useEffect, useState } from 'react'
import { fetchApprovals, resolveApproval, useResource } from '../api'
import type { ApprovalRequest } from '../types'
import { AlertBanner, DemoDataChip, RiskChip, StatusChip } from '../components/DecisionBadge'
import { Button, Card, EmptyState, ErrorState, LoadingState, SectionTitle } from '../components/ui'
import { expiresInLabel, countdownLabel } from '../lib/utils'

export function Approvals() {
  const { loading, error, data, source, reload } = useResource(fetchApprovals)
  const [items, setItems] = useState<ApprovalRequest[]>([])
  const [reasonById, setReasonById] = useState<Record<string, string>>({})
  const [toast, setToast] = useState<string | null>(null)
  const [actingId, setActingId] = useState<string | null>(null)
  const [now, setNow] = useState(Date.now())

  useEffect(() => {
    if (data) setItems(data)
  }, [data])

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  const act = async (id: string, kind: 'approve' | 'deny') => {
    const reason = (reasonById[id] ?? '').trim()
    if (!reason) return
    setActingId(id)
    try {
      await resolveApproval(id, kind, reason)
      setItems((prev) => prev.filter((x) => x.id !== id))
      setToast(
        kind === 'approve'
          ? 'Approved once — this exact action only. No permanent access granted.'
          : 'Denied. The agent cannot execute this action.',
      )
    } catch (err) {
      setToast(err instanceof Error ? err.message : 'Could not update this approval.')
    } finally {
      setActingId(null)
    }
  }

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Actions that need a human"
        subtitle="Some requests may be legitimate but are too sensitive for an agent to execute alone."
        action={source === 'demo' && !loading ? <DemoDataChip /> : null}
      />

      <AlertBanner tone="warn">
        Approval permits one exact action. It does not give the agent permanent access.
      </AlertBanner>

      {toast ? (
        <Card className="border-aj-brand/40 bg-aj-brand/10 px-4 py-3 text-sm text-aj-brand">{toast}</Card>
      ) : null}

      {loading ? <LoadingState label="Loading approvals" /> : null}
      {error ? (
        <ErrorState title="Could not load approvals" message={error.message} details={error.details} onRetry={reload} />
      ) : null}

      {!loading && !error ? (
        <div className="grid gap-4">
          {items.map((item) => (
            <ApprovalCard
              key={item.id}
              item={item}
              now={now}
              reason={reasonById[item.id] ?? ''}
              busy={actingId === item.id}
              onReason={(v) => setReasonById((m) => ({ ...m, [item.id]: v }))}
              onApprove={() => void act(item.id, 'approve')}
              onDeny={() => void act(item.id, 'deny')}
            />
          ))}
          {items.length === 0 ? (
            <EmptyState title="No pending approvals" subtitle="Queue is clear. Sensitive actions will pause here." />
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

function ApprovalCard({
  item,
  reason,
  busy,
  now,
  onReason,
  onApprove,
  onDeny,
}: {
  item: ApprovalRequest
  reason: string
  busy: boolean
  now: number
  onReason: (v: string) => void
  onApprove: () => void
  onDeny: () => void
}) {
  const [startedAt] = useState(() => Date.now())
  const expiresIn = item.expiresAt ? expiresInLabel(item.expiresAt) : countdownLabel(item.expiresIn, startedAt, now)
  const expired = expiresIn === 'Expired' || item.expired
  const ready = reason.trim().length > 0 && !expired && !busy

  return (
    <Card hover className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-display text-xl font-bold">{item.action}</p>
          <p className="mt-1 text-sm text-aj-muted">Requesting agent: {item.agent}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <RiskChip risk={item.risk} />
          <StatusChip tone={item.verified ? 'allow' : 'block'}>
            Source {item.verified ? 'verified' : 'unverified'}
          </StatusChip>
          <StatusChip tone={expired ? 'block' : 'approve'}>
            {expired ? 'Expired' : `Expires in ${expiresIn}`}
          </StatusChip>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Meta label="Human or system actor" value={item.actor} />
        <Meta label="Source" value={item.source} />
        <Meta label="Resource affected" value={item.resource} />
      </div>

      <p className="mt-4 text-sm text-aj-muted">
        <span className="font-medium text-aj-text">Why approval is needed: </span>
        {item.why}
      </p>

      <label className="mt-4 block text-sm">
        <span className="text-aj-muted">Reason required before Approve once or Deny</span>
        <textarea
          value={reason}
          onChange={(e) => onReason(e.target.value)}
          rows={2}
          className="mt-1 w-full rounded-xl border border-aj-border bg-aj-panel px-3 py-2 text-sm text-aj-text outline-none focus:border-aj-brand"
          placeholder="Why are you approving or denying this exact action?"
          required
        />
      </label>
      {!reason.trim() ? (
        <p className="mt-2 text-xs text-aj-approve">Type a reason to enable Approve once and Deny.</p>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <Button variant="allow" onClick={onApprove} disabled={!ready}>
          Approve once
        </Button>
        <Button variant="danger" onClick={onDeny} disabled={!ready}>
          Deny
        </Button>
        <Button variant="secondary">View evidence</Button>
      </div>
    </Card>
  )
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-aj-border bg-aj-panel/60 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-aj-muted">{label}</p>
      <p className="mt-1 text-sm">{value}</p>
    </div>
  )
}
