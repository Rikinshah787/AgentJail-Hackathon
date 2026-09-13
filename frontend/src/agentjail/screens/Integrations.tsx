import { useState } from 'react'
import { Code2, Plug, Shield, ShieldCheck, ShieldX } from 'lucide-react'
import { ApiError, authorizeMcpStyle } from '../api'
import type { Decision } from '../types'
import { Button, Card, SectionTitle } from '../components/ui'
import { AlertBanner, DecisionBadge } from '../components/DecisionBadge'

const INTEGRATIONS = [
  { name: 'MCP', blurb: 'Wrap each MCP tool handler with authorize() before execution.', live: true },
  { name: 'LangGraph', blurb: 'Gate tool nodes before the graph continues.', live: false },
  { name: 'OpenAI Agents', blurb: 'Intercept function calls at the runtime boundary.', live: false },
  { name: 'Custom Python', blurb: 'One authorize() call around your tool dispatcher.', live: true },
  { name: 'REST API', blurb: 'POST /api/v1/authorize from any language stack.', live: true },
]

const SAMPLE = `# MCP-style wrapper (conceptual)
async def call_tool(name, args):
    decision = await agentjail.authorize(tool_call)
    if decision.decision == "allow":
        return await execute(name, args)   # only then
    if decision.decision == "approval_required":
        return await wait_for_human(decision)
    raise PermissionError(decision.reason)  # deny — never execute`

type LiveResult = {
  kind: 'attack' | 'safe'
  decision: Decision
  reason: string
  executed: boolean
}

export function Integrations() {
  const [busy, setBusy] = useState<'attack' | 'safe' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<LiveResult | null>(null)

  async function run(kind: 'attack' | 'safe') {
    setBusy(kind)
    setError(null)
    try {
      const out = await authorizeMcpStyle(kind)
      setResult({ kind, ...out })
    } catch (err) {
      setResult(null)
      setError(err instanceof ApiError ? err.details : err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="space-y-8">
      <SectionTitle
        title="Protect an agent"
        subtitle="Sit AgentJail immediately before tool execution — including MCP tool handlers."
      />

      <Card className="border-aj-brand/25 bg-aj-brand/[0.06] p-5 sm:p-6">
        <div className="flex flex-wrap items-start gap-3">
          <Shield className="mt-0.5 size-5 text-aj-brand" aria-hidden />
          <div className="min-w-0 flex-1">
            <h3 className="font-display text-xl font-bold">Live MCP-style authorize</h3>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-aj-muted">
              This is not a mock card. It calls the real <code className="text-aj-text">POST /api/v1/authorize</code>{' '}
              boundary an MCP server would wrap around tools. Attack should deny; safe restart should allow.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button size="sm" variant="danger" disabled={busy !== null} onClick={() => void run('attack')}>
                {busy === 'attack' ? 'Authorizing…' : 'Simulate poisoned MCP tool'}
              </Button>
              <Button size="sm" variant="allow" disabled={busy !== null} onClick={() => void run('safe')}>
                {busy === 'safe' ? 'Authorizing…' : 'Simulate safe MCP restart'}
              </Button>
            </div>
            {error ? (
              <p className="mt-3 text-sm text-aj-block" role="alert">
                {error}
              </p>
            ) : null}
            {result ? (
              <div className="mt-4 rounded-xl border border-aj-border bg-aj-bg/80 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <DecisionBadge decision={result.decision} />
                  <span className="text-xs text-aj-muted">
                    {result.kind === 'attack' ? 'Poisoned MCP args' : 'Signed restart'} · executed=
                    {String(result.executed)}
                  </span>
                </div>
                <p className="mt-3 text-sm text-aj-text">{result.reason}</p>
                <p className="mt-2 flex items-center gap-1.5 text-xs text-aj-muted">
                  {result.executed ? (
                    <>
                      <ShieldCheck className="size-3.5 text-aj-allow" /> Tool allowed to run (simulated executor)
                    </>
                  ) : (
                    <>
                      <ShieldX className="size-3.5 text-aj-block" /> Tool never executed
                    </>
                  )}
                </p>
              </div>
            ) : null}
          </div>
        </div>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {INTEGRATIONS.map((item) => (
          <Card key={item.name} hover className="p-5">
            <div className="flex items-center gap-2 text-aj-brand">
              <Plug className="size-5" aria-hidden />
              <h3 className="font-display text-lg font-bold">{item.name}</h3>
              {item.live ? (
                <span className="ml-auto rounded-md bg-aj-allow/15 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-aj-allow">
                  Live API
                </span>
              ) : (
                <span className="ml-auto rounded-md bg-white/5 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-aj-muted">
                  Pattern
                </span>
              )}
            </div>
            <p className="mt-2 text-sm text-aj-muted">{item.blurb}</p>
          </Card>
        ))}
      </div>

      <Card className="p-6">
        <div className="mb-2 flex items-center gap-2 text-aj-muted">
          <Code2 className="size-4" aria-hidden />
          <span className="text-sm font-medium">MCP wrapper pattern</span>
        </div>
        <pre className="overflow-x-auto rounded-xl border border-aj-border bg-aj-bg p-4 text-sm leading-relaxed text-aj-text">
          {SAMPLE}
        </pre>
      </Card>

      <AlertBanner tone="info">
        Full MCP server packaging is next. The product boundary that matters — authorize before execute — is live now.
      </AlertBanner>
    </div>
  )
}
