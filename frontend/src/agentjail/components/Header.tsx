import { Bell, ChevronDown, Presentation, RotateCcw } from 'lucide-react'
import { PROTECTED_AGENTS } from '../data/mock'
import { Button } from './ui'
import { Logo } from './Logo'
import { cn } from '../lib/utils'

export function Header({
  demoMode,
  onToggleDemo,
  agent,
  onAgentChange,
  onOpenDemoGuide,
  onResetDemo,
  pendingCount = 0,
  resetting = false,
}: {
  demoMode: boolean
  onToggleDemo: () => void
  agent: string
  onAgentChange: (v: string) => void
  onOpenDemoGuide: () => void
  onResetDemo: () => void
  pendingCount?: number
  resetting?: boolean
}) {
  return (
    <header className="sticky top-0 z-40 flex h-[64px] w-full shrink-0 items-center justify-between gap-2 border-b border-white/5 bg-aj-panel/90 px-3 backdrop-blur-xl sm:h-[68px] sm:px-5">
      <div className="flex shrink-0 items-center gap-2.5">
        <Logo size={36} />
        <div className="min-w-0">
          <div className="flex items-baseline gap-2.5">
            <h1 className="truncate font-display text-base font-bold tracking-tight sm:text-[1.15rem]">AgentJail</h1>
            <span className="hidden h-4 w-px bg-white/10 xl:block" />
            <span className="hidden text-xs text-aj-muted xl:inline">Runtime security for AI agents</span>
          </div>
          <p className="hidden truncate text-xs text-aj-muted min-[360px]:block sm:hidden">Runtime security</p>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-1.5 sm:gap-2.5">
        <div className="hidden items-center gap-2 rounded-full border border-aj-allow/25 bg-aj-allow/10 px-3 py-1.5 text-xs font-medium text-aj-allow md:flex">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-aj-allow opacity-50" />
            <span className="relative inline-flex size-2 rounded-full bg-aj-allow" />
          </span>
          Protection active
        </div>

        <label className="relative hidden items-center lg:flex">
          <span className="sr-only">Protected agent</span>
          <select
            value={agent}
            onChange={(e) => onAgentChange(e.target.value)}
            className="appearance-none rounded-xl border border-aj-border bg-aj-card/80 py-2 pl-3 pr-8 text-sm text-aj-text outline-none hover:border-aj-brand/40"
          >
            {PROTECTED_AGENTS.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-2.5 size-3.5 text-aj-muted" aria-hidden />
        </label>

        <button
          type="button"
          className="relative hidden rounded-xl border border-aj-border p-2 text-aj-muted hover:bg-white/5 hover:text-aj-text min-[390px]:block"
          aria-label={pendingCount ? `Notifications, ${pendingCount} pending` : 'Notifications'}
        >
          <Bell className="size-4" />
          {pendingCount > 0 ? (
            <span className="absolute -right-1 -top-1 flex size-4 items-center justify-center rounded-full bg-aj-block text-[10px] font-bold text-white">
              {pendingCount > 9 ? '9+' : pendingCount}
            </span>
          ) : null}
        </button>

        <button
          type="button"
          onClick={onToggleDemo}
          className={cn(
            'inline-flex items-center gap-1.5 rounded-full border px-2 py-1.5 text-[11px] font-semibold transition sm:gap-2 sm:px-2.5 sm:text-xs',
            demoMode
              ? 'border-aj-brand/40 bg-aj-brand/15 text-aj-brand'
              : 'border-aj-border text-aj-muted hover:text-aj-text',
          )}
          aria-pressed={demoMode}
        >
          <span
            className={cn(
              'relative h-4 w-7 rounded-full transition',
              demoMode ? 'bg-aj-brand' : 'bg-aj-border',
            )}
          >
            <span
              className={cn(
                'absolute top-0.5 size-3 rounded-full bg-white transition',
                demoMode ? 'left-3.5' : 'left-0.5',
              )}
            />
          </span>
          <span className="hidden min-[340px]:inline">Demo</span>
        </button>

        <Button size="sm" variant="ghost" className="hidden md:inline-flex" onClick={onResetDemo} disabled={resetting}>
          <RotateCcw className={cn('size-3.5', resetting && 'animate-spin')} />
          Reset
        </Button>
        <Button size="sm" variant="secondary" className="hidden sm:inline-flex" onClick={onOpenDemoGuide}>
          <Presentation className="size-3.5" />
          Guided demo
        </Button>
      </div>
    </header>
  )
}
