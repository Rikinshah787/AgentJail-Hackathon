import { fetchDashboard, fetchWeaveStatus, useResource } from '../api'
import {
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  Fingerprint,
  History,
  Play,
  ScanSearch,
  Shield,
  ShieldCheck,
  ShieldX,
  UserRoundCheck,
  Waypoints,
} from 'lucide-react'
import type { DecisionCard as DecisionCardType, NavId } from '../types'
import { ClockChip, DecisionBadge, DemoDataChip, RiskChip } from '../components/DecisionBadge'
import { Button, Card, ErrorState, LoadingState, MetricCard, SectionTitle } from '../components/ui'
import { cn } from '../lib/utils'

const ACCENT: Record<DecisionCardType['decision'], string> = {
  allow: 'border-l-aj-allow',
  block: 'border-l-aj-block',
  approval_required: 'border-l-aj-approve',
}

function DecisionCardView({ item }: { item: DecisionCardType }) {
  return (
    <Card hover className={cn('flex h-full flex-col border-l-[3px] p-5', ACCENT[item.decision])}>
      <div className="flex flex-wrap items-center gap-2">
        <DecisionBadge decision={item.decision} />
        <RiskChip risk={item.risk} />
        <ClockChip label={item.timeAgo} />
      </div>
      <p className="mt-3 text-base font-medium leading-snug text-aj-text">{item.title}</p>
      <p className="mt-2 text-sm leading-relaxed text-aj-muted">
        <span className="font-medium text-aj-text/80">Reason: </span>
        {item.reason}
      </p>
      <p className="mt-auto pt-4 font-mono text-xs text-aj-muted">Tool: {item.tool}</p>
    </Card>
  )
}

const FLOW = [
  {
    n: 1,
    title: 'Agent reads content',
    body: 'An agent reads an email, ticket, document, or website.',
  },
  {
    n: 2,
    title: 'Agent requests a tool',
    body: 'The agent tries to restart a service, send data, or change infrastructure.',
  },
  {
    n: 3,
    title: 'AgentJail checks it',
    body: 'AgentJail verifies the source, permissions, risk, and attack history.',
  },
  {
    n: 4,
    title: 'Decision',
    body: 'Allow, Block, or Ask a Human.',
  },
]

const DIFFERENTIATORS = [
  { t: 'Controls actions', d: 'Not just model responses — tool calls before execution.', icon: Waypoints },
  { t: 'Verifies the source', d: 'Where the instruction came from matters.', icon: ScanSearch },
  { t: 'Allow · Block · Approve', d: 'Three clear outcomes humans can understand.', icon: ShieldCheck },
  { t: 'Remembers attacks', d: 'Scoped security scars recognize repeated patterns.', icon: History },
]

export function ControlRoom({
  agent,
  onNavigate,
}: {
  agent: string
  onNavigate: (id: NavId) => void
}) {
  const { loading, error, data, source, reload } = useResource(fetchDashboard)
  const weave = useResource(fetchWeaveStatus)
  const metrics = data
  const weaveUrl =
    weave.data?.weaveTracesUrl ||
    'https://wandb.ai/rshah88-arizona-state-university/agent-jail/weave/traces?view=traces_default'

  return (
    <div className="space-y-8 md:space-y-10">
      <section className="overflow-hidden rounded-2xl border border-aj-border bg-aj-card p-5 sm:p-7">
        <div className="grid items-center gap-7 md:grid-cols-[1.12fr_0.88fr]">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-aj-brand">Control Room</p>
          <h2 className="mt-3 max-w-xl font-display text-3xl font-bold leading-[1.08] tracking-tight sm:text-[2.15rem] xl:text-[2.45rem]">
            Give agents authority without giving them the keys.
          </h2>
          <p className="mt-4 max-w-xl text-base leading-relaxed text-aj-muted">
            AgentJail checks the request, who sent it, and the blast radius immediately before an agent calls a tool.
          </p>
          <div className="mt-6 flex items-center gap-4">
            <Button size="lg" onClick={() => onNavigate('live-demo')}>
              <Play className="size-4" /> Run the 90-second demo
            </Button>
            <button type="button" className="text-sm font-semibold text-aj-muted hover:text-aj-text" onClick={() => onNavigate('breach-arena')}>
              Open the arena →
            </button>
          </div>
        </div>

        <Card className="relative overflow-hidden border-aj-border bg-aj-panel p-5 sm:p-6">
          <div className="relative">
            <div className="flex items-start gap-3.5">
              <span className="rounded-xl bg-aj-brand/15 p-3 text-aj-brand">
                <Shield className="size-7" aria-hidden />
              </span>
              <div>
                <p className="font-display text-xl font-bold leading-snug">AgentJail is protecting {agent}</p>
                <p className="mt-1 text-sm text-aj-muted">Every tool action is being checked</p>
              </div>
            </div>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <span className="inline-flex items-center gap-2 rounded-full border border-aj-allow/40 bg-aj-allow/15 px-3 py-1.5 text-sm font-semibold text-aj-allow">
                <CheckCircle2 className="size-4" aria-hidden />
                {metrics?.protectionActive === false ? 'Standby' : 'Active'}
              </span>
              <span className="text-sm text-aj-muted">
                {loading ? 'Checking protection status…' : 'Last checked a few seconds ago'}
              </span>
            </div>
            <ul className="mt-5 space-y-2 text-sm text-aj-muted">
              {['Who asked', 'Where the instruction came from', 'How dangerous the action is'].map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <CheckCircle2 className="size-3.5 text-aj-brand" aria-hidden />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </Card>
        </div>
      </section>

      <section>
        <div className="mb-4 flex items-center justify-between gap-3">
          <h3 className="font-display text-lg font-bold">Protection snapshot</h3>
          {source === 'demo' && !loading ? <DemoDataChip /> : null}
        </div>
        {loading ? <LoadingState label="Loading protection snapshot" /> : null}
        {error ? (
          <ErrorState
            title="Could not load dashboard"
            message={error.message}
            details={error.details}
            onRetry={reload}
          />
        ) : null}
        {!loading && !error && metrics ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard icon={ShieldX} label="Attacks blocked" value={metrics.attacksBlocked} tone="block" />
            <MetricCard icon={CheckCircle2} label="Safe actions allowed" value={metrics.safeAllowed} tone="allow" />
            <MetricCard
              icon={UserRoundCheck}
              label="Awaiting approval"
              value={metrics.awaitingApproval}
              tone="approve"
            />
            <MetricCard icon={Fingerprint} label="Repeated attacks recognized" value={metrics.scarMatches} tone="brand" />
          </div>
        ) : null}
      </section>

      <Card className="border-aj-border bg-aj-panel p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-aj-muted">Observability · W&amp;B Weave</p>
            <h3 className="mt-2 font-display text-xl font-bold">Every decision has an audit trail.</h3>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-aj-muted">
              Open the exact tool request, policy checks, scar matches, and executor outcome in Weave.
            </p>
            <p className="mt-2 text-xs text-aj-muted">
              Status:{' '}
              {weave.loading
                ? 'checking…'
                : weave.data?.weaveEnabled
                  ? `Tracing ON · ${weave.data.weaveProject}`
                  : 'Tracing off — set WANDB_API_KEY on the backend'}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <a
              href={
                weave.data?.weaveAgentsUrl ||
                'https://wandb.ai/rshah88-arizona-state-university/agent-jail/weave/agents'
              }
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-xl border border-aj-brand/40 bg-aj-brand/15 px-4 py-2.5 text-sm font-semibold text-aj-brand hover:bg-aj-brand/25"
            >
              Open Weave Agents
              <ExternalLink className="size-3.5" />
            </a>
            <a
              href={weaveUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-xl border border-aj-border bg-aj-card px-4 py-2.5 text-sm font-medium text-aj-text hover:border-aj-brand/40"
            >
              Traces
              <ExternalLink className="size-3.5" />
            </a>
          </div>
        </div>
      </Card>

      <section>
        <SectionTitle
          title="How AgentJail works"
          subtitle="Airport security for AI agent actions — inspect before anything real happens."
        />
        <div className="grid gap-3 md:grid-cols-4">
          {FLOW.map((step, i) => (
            <div key={step.n} className="relative">
              <Card className="h-full p-4">
                <div className="flex items-center gap-2">
                  <span className="flex size-7 items-center justify-center rounded-full bg-aj-brand/15 text-xs font-bold text-aj-brand">
                    {step.n}
                  </span>
                  <p className="font-display text-[15px] font-bold leading-tight">{step.title}</p>
                </div>
                <p className="mt-3 text-sm leading-relaxed text-aj-muted">{step.body}</p>
              </Card>
              {i < FLOW.length - 1 ? (
                <div
                  className="aj-flow-arrow pointer-events-none absolute -right-3 top-8 z-10 hidden text-aj-brand md:block"
                  style={{ animationDelay: `${i * 0.35}s` }}
                >
                  <ArrowRight className="size-5" aria-hidden />
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </section>

      <section>
        <SectionTitle title="Recent decisions" subtitle="What just happened — in plain language, not a dense table." />
        {metrics?.recent?.length ? (
          <div className="grid gap-4 lg:grid-cols-3">
            {metrics.recent.map((d) => (
              <DecisionCardView key={d.id} item={d} />
            ))}
          </div>
        ) : !loading && !error ? (
          <Card className="p-8 text-center text-aj-muted">No decisions yet. Run a live demo to generate one.</Card>
        ) : null}
      </section>

      <section>
        <Card className="p-6 md:p-8">
          <h3 className="font-display text-2xl font-bold">What makes AgentJail different</h3>
          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {DIFFERENTIATORS.map((x) => {
              const Icon = x.icon
              return (
                <div key={x.t} className="rounded-xl border border-white/6 bg-aj-panel/50 p-4">
                  <div className="mb-2.5 text-aj-brand">
                    <Icon className="size-5" aria-hidden />
                  </div>
                  <p className="font-semibold">{x.t}</p>
                  <p className="mt-1 text-sm leading-relaxed text-aj-muted">{x.d}</p>
                </div>
              )
            })}
          </div>

          <div className="mt-8 grid gap-3 md:grid-cols-3">
            <div className="rounded-xl border border-white/6 p-4">
              <p className="text-xs uppercase tracking-wide text-aj-muted">Prompt filter</p>
              <p className="mt-2 font-semibold">Checks text</p>
            </div>
            <div className="rounded-xl border border-white/6 p-4">
              <p className="text-xs uppercase tracking-wide text-aj-muted">Traditional RBAC</p>
              <p className="mt-2 font-semibold">Checks static identity permissions</p>
            </div>
            <div className="rounded-xl border border-aj-brand/40 bg-aj-brand/10 p-4">
              <p className="text-xs uppercase tracking-wide text-aj-brand">AgentJail</p>
              <p className="mt-2 text-sm font-semibold leading-relaxed">
                Checks the actor, instruction source, requested action, policy, approval, and attack history immediately
                before execution
              </p>
            </div>
          </div>
        </Card>
      </section>

      <section>
        <Card className="relative overflow-hidden border-aj-brand/25 bg-gradient-to-br from-aj-brand/20 via-aj-card to-aj-panel p-8 md:p-10">
          <div className="absolute -right-16 -top-16 size-56 rounded-full bg-aj-brand/20 blur-3xl" />
          <div className="relative">
            <h3 className="max-w-2xl font-display text-3xl font-extrabold tracking-tight md:text-4xl">
              Let agents work without giving them unlimited authority.
            </h3>
            <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-aj-muted">
              AgentJail provides a security checkpoint between AI reasoning and real-world execution.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Button size="lg" onClick={() => onNavigate('live-demo')}>
                Run the attack demo
              </Button>
              <Button size="lg" variant="secondary" onClick={() => onNavigate('integrations')}>
                Protect an agent
              </Button>
            </div>
          </div>
        </Card>
      </section>
    </div>
  )
}
