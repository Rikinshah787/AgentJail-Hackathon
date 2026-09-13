import { useCallback, useEffect, useState } from 'react'
import './agentjail.css'
import { fetchApprovals, resetDemo } from './api'
import type { NavId } from './types'
import { PROTECTED_AGENTS } from './data/mock'
import { Header } from './components/Header'
import { NAV_ITEMS, Sidebar } from './components/Sidebar'
import { DemoGuide } from './components/DemoGuide'
import { ControlRoom } from './screens/ControlRoom'
import { LiveDemo } from './screens/LiveDemo'
import { Incidents } from './screens/Incidents'
import { Approvals } from './screens/Approvals'
import { Scars } from './screens/Scars'
import { Evaluations } from './screens/Evaluations'
import { Policies } from './screens/Policies'
import { Integrations } from './screens/Integrations'
import { BreachArena } from './screens/BreachArena'
import { cn } from './lib/utils'

export default function AgentJailApp() {
  const [nav, setNav] = useState<NavId>('control-room')
  const [demoMode, setDemoMode] = useState(true)
  const [agent, setAgent] = useState<string>(PROTECTED_AGENTS[0])
  const [guideOpen, setGuideOpen] = useState(false)
  const [demoScene, setDemoScene] = useState<number | null>(null)
  const [resetKey, setResetKey] = useState(0)
  const [resetting, setResetting] = useState(false)
  const [pendingCount, setPendingCount] = useState(0)

  const onJump = useCallback((scene: number) => {
    setDemoScene(scene)
    if (scene <= 3) setNav('live-demo')
    else setNav('approvals')
  }, [])

  const onReset = useCallback(() => {
    setResetting(true)
    void resetDemo()
      .catch(() => undefined)
      .finally(() => {
        setResetKey((k) => k + 1)
        setDemoScene(null)
        setNav('control-room')
        setResetting(false)
      })
  }, [])

  useEffect(() => {
    let cancelled = false
    fetchApprovals()
      .then((res) => {
        if (!cancelled) setPendingCount(res.data.length)
      })
      .catch(() => {
        if (!cancelled) setPendingCount(0)
      })
    return () => {
      cancelled = true
    }
  }, [resetKey])

  return (
    <div className="agentjail-root flex min-h-screen flex-col">
      <Header
        demoMode={demoMode}
        onToggleDemo={() => setDemoMode((v) => !v)}
        agent={agent}
        onAgentChange={setAgent}
        onOpenDemoGuide={() => {
          setGuideOpen(true)
          setNav('live-demo')
        }}
        onResetDemo={onReset}
        pendingCount={pendingCount}
        resetting={resetting}
      />
      <div className="flex min-h-0 flex-1">
        <div className="sticky top-[68px] hidden h-[calc(100vh-68px)] md:flex">
          <Sidebar active={nav} onNavigate={setNav} />
        </div>
        <main className="min-w-0 flex-1 overflow-y-auto px-3 py-5 sm:px-5 md:px-8 md:py-8">
          <div className="mx-auto max-w-6xl">
              <label className="mb-5 block min-[720px]:hidden md:hidden">
              <span className="sr-only">Current section</span>
              <select
                value={nav}
                onChange={(event) => setNav(event.target.value as NavId)}
                className="w-full rounded-xl border border-aj-border bg-aj-card px-3 py-2.5 text-sm font-semibold text-aj-text outline-none"
              >
                {NAV_ITEMS.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
              <div className="mb-5 hidden gap-2 overflow-x-auto pb-1 min-[720px]:flex md:hidden">
              {NAV_ITEMS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setNav(item.id)}
                  className={cn(
                    'shrink-0 rounded-full border px-3 py-1.5 text-xs font-medium',
                    nav === item.id
                      ? 'border-aj-brand bg-aj-brand/20 text-aj-brand'
                      : 'border-aj-border text-aj-muted',
                    item.emphasize && nav !== item.id && 'border-aj-brand/40 text-aj-brand',
                  )}
                >
                  {item.label}
                </button>
              ))}
            </div>

            {demoMode ? (
              <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-aj-brand/25 bg-aj-brand/10 px-3 py-1.5 text-xs text-aj-brand">
                <span className="size-1.5 rounded-full bg-aj-brand" />
                Demo Mode — simulated tools only. Nothing real is executed.
              </p>
            ) : null}

            <div key={`${resetKey}-${nav}`} className="aj-page">
              {nav === 'control-room' ? <ControlRoom agent={agent} onNavigate={setNav} /> : null}
              {nav === 'live-demo' ? <LiveDemo demoScene={guideOpen ? demoScene : null} /> : null}
              {nav === 'breach-arena' ? <BreachArena /> : null}
              {nav === 'incidents' ? <Incidents /> : null}
              {nav === 'approvals' ? <Approvals /> : null}
              {nav === 'scars' ? <Scars /> : null}
              {nav === 'evaluations' ? <Evaluations /> : null}
              {nav === 'policies' ? <Policies /> : null}
              {nav === 'integrations' ? <Integrations /> : null}
            </div>
          </div>
        </main>
      </div>

      <DemoGuide
        open={guideOpen}
        onClose={() => {
          setGuideOpen(false)
          setDemoScene(null)
        }}
        onJump={onJump}
        onReset={onReset}
      />
    </div>
  )
}
