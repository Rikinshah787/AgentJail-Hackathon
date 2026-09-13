import {
  Activity,
  Box,
  ClipboardCheck,
  FlaskConical,
  LayoutDashboard,
  Plug,
  Scale,
  Shield,
  Sparkles,
} from 'lucide-react'
import type { NavId } from '../types'
import { cn } from '../lib/utils'

export const NAV_ITEMS: { id: NavId; label: string; icon: typeof LayoutDashboard; emphasize?: boolean }[] = [
  { id: 'control-room', label: 'Control Room', icon: LayoutDashboard },
  { id: 'live-demo', label: 'Live Demo', icon: Sparkles, emphasize: true },
  { id: 'breach-arena', label: 'Breach Arena', icon: Box },
  { id: 'incidents', label: 'Incidents', icon: Shield },
  { id: 'approvals', label: 'Approvals', icon: ClipboardCheck },
  { id: 'scars', label: 'Scars', icon: Activity },
  { id: 'evaluations', label: 'Evaluations', icon: FlaskConical },
  { id: 'policies', label: 'Policies', icon: Scale },
  { id: 'integrations', label: 'Integrations', icon: Plug },
]

export function Sidebar({
  active,
  onNavigate,
}: {
  active: NavId
  onNavigate: (id: NavId) => void
}) {
  return (
    <aside className="flex w-[232px] shrink-0 flex-col border-r border-white/5 bg-aj-panel/70 px-3 py-5">
      <p className="mb-3 px-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-aj-muted/80">
        Workspace
      </p>
      <nav className="flex flex-1 flex-col gap-1" aria-label="AgentJail">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          const isActive = active === item.id
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              className={cn(
                'relative flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-sm transition',
                isActive
                  ? 'bg-white/[0.06] text-aj-text'
                  : 'text-aj-muted hover:bg-white/[0.04] hover:text-aj-text',
                item.emphasize && !isActive && 'mt-1 mb-1 border border-aj-brand/25 bg-aj-brand/[0.07] text-aj-brand',
                item.emphasize && isActive && 'aj-brand-glow mb-1 mt-1 border border-aj-brand/35 bg-aj-brand/15',
              )}
            >
              {isActive ? (
                <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-full bg-aj-brand" />
              ) : null}
              <Icon className={cn('size-4', item.emphasize && 'text-aj-brand')} aria-hidden />
              <span className={cn(item.emphasize && 'font-semibold')}>{item.label}</span>
              {item.emphasize ? (
                <span className="ml-auto rounded-md bg-aj-brand/20 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-aj-brand">
                  Demo
                </span>
              ) : null}
            </button>
          )
        })}
      </nav>
      <div className="mt-4 rounded-2xl border border-white/6 bg-gradient-to-br from-aj-brand/15 to-aj-card p-3.5">
        <p className="text-xs font-semibold text-aj-text">Airport security for agents</p>
        <p className="mt-1.5 text-[11px] leading-relaxed text-aj-muted">
          The agent proposes an action. AgentJail inspects it. Only authorized actions pass through.
        </p>
      </div>
    </aside>
  )
}
