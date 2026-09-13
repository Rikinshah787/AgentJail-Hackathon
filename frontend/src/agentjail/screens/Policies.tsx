import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { fetchPolicies, useResource } from '../api'
import { DemoDataChip, StatusChip } from '../components/DecisionBadge'
import { Card, EmptyState, ErrorState, LoadingState, SectionTitle } from '../components/ui'
import { cn } from '../lib/utils'

export function Policies() {
  const { loading, error, data, source, reload } = useResource(fetchPolicies)
  const [openId, setOpenId] = useState<string | null>(null)
  const policies = data ?? []

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Policies"
        subtitle="Rules written in plain language first. Advanced JSON stays collapsed."
        action={source === 'demo' && !loading ? <DemoDataChip /> : null}
      />

      {loading ? <LoadingState label="Loading policies" /> : null}
      {error ? (
        <ErrorState title="Could not load policies" message={error.message} details={error.details} onRetry={reload} />
      ) : null}

      {!loading && !error && policies.length === 0 ? (
        <EmptyState title="No policies yet" subtitle="Authorization rules will appear here once the gateway is seeded." />
      ) : null}

      {!loading && !error ? (
        <div className="grid gap-4">
          {policies.map((policy) => {
            const open = openId === policy.id
            return (
              <Card key={policy.id} hover className="p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="font-display text-xl font-bold">{policy.name}</h3>
                    <p className="mt-2 max-w-3xl text-aj-muted">{policy.plainEnglish}</p>
                  </div>
                  <StatusChip
                    tone={
                      policy.decision === 'Block' ? 'block' : policy.decision === 'Allow' ? 'allow' : 'approve'
                    }
                  >
                    {policy.decision}
                  </StatusChip>
                </div>

                <div className="mt-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-aj-muted">Applies to</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {policy.appliesTo.map((t) => (
                      <span
                        key={t}
                        className="rounded-lg border border-aj-border bg-aj-panel px-2.5 py-1 font-mono text-xs"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>

                <button
                  type="button"
                  className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-aj-brand"
                  onClick={() => setOpenId(open ? null : policy.id)}
                  aria-expanded={open}
                >
                  Advanced JSON / code view
                  <ChevronDown className={cn('size-4 transition', open && 'rotate-180')} />
                </button>
                {open ? (
                  <pre className="mt-3 overflow-x-auto rounded-xl border border-aj-border bg-aj-panel p-4 text-xs text-aj-muted">
                    {policy.advancedJson}
                  </pre>
                ) : null}
              </Card>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}
