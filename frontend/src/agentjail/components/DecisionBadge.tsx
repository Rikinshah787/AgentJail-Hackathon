import type { ReactNode } from 'react'
import {
  CheckCircle2,
  Clock3,
  ShieldAlert,
  ShieldX,
  UserRoundCheck,
} from 'lucide-react'
import type { Decision } from '../types'
import { cn } from '../lib/utils'

const CONFIG: Record<
  Decision,
  { label: string; className: string; icon: typeof CheckCircle2 }
> = {
  allow: {
    label: 'Allowed',
    className: 'bg-aj-allow/15 text-aj-allow border-aj-allow/40',
    icon: CheckCircle2,
  },
  block: {
    label: 'Blocked',
    className: 'bg-aj-block/15 text-aj-block border-aj-block/40',
    icon: ShieldX,
  },
  approval_required: {
    label: 'Approval required',
    className: 'bg-aj-approve/15 text-aj-approve border-aj-approve/40',
    icon: UserRoundCheck,
  },
}

export function DecisionBadge({
  decision,
  size = 'md',
}: {
  decision: Decision
  size?: 'sm' | 'md' | 'lg'
}) {
  const cfg = CONFIG[decision]
  const Icon = cfg.icon
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border font-medium',
        cfg.className,
        size === 'sm' && 'px-2 py-0.5 text-xs',
        size === 'md' && 'px-2.5 py-1 text-sm',
        size === 'lg' && 'px-3 py-1.5 text-base',
      )}
    >
      <Icon className={cn(size === 'sm' ? 'size-3.5' : 'size-4')} aria-hidden />
      {cfg.label}
    </span>
  )
}

export function RiskChip({ risk }: { risk: string }) {
  const tone =
    risk === 'Critical' || risk === 'High'
      ? 'text-aj-block border-aj-block/30 bg-aj-block/10'
      : risk === 'Medium'
        ? 'text-aj-approve border-aj-approve/30 bg-aj-approve/10'
        : 'text-aj-allow border-aj-allow/30 bg-aj-allow/10'
  return (
    <span className={cn('rounded-full border px-2 py-0.5 text-xs font-medium', tone)}>
      {risk} risk
    </span>
  )
}

export function StatusChip({
  children,
  tone = 'neutral',
}: {
  children: ReactNode
  tone?: 'neutral' | 'allow' | 'block' | 'approve' | 'brand'
}) {
  const map = {
    neutral: 'border-aj-border bg-aj-card text-aj-muted',
    allow: 'border-aj-allow/40 bg-aj-allow/10 text-aj-allow',
    block: 'border-aj-block/40 bg-aj-block/10 text-aj-block',
    approve: 'border-aj-approve/40 bg-aj-approve/10 text-aj-approve',
    brand: 'border-aj-brand/40 bg-aj-brand/10 text-aj-brand',
  }
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium', map[tone])}>
      {children}
    </span>
  )
}

export function ClockChip({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-xs text-aj-muted">
      <Clock3 className="size-3.5" aria-hidden />
      {label}
    </span>
  )
}

export function DemoDataChip() {
  return <StatusChip tone="brand">Demo data</StatusChip>
}

export function AlertBanner({
  children,
  tone = 'warn',
}: {
  children: ReactNode
  tone?: 'warn' | 'info' | 'danger'
}) {
  const styles = {
    warn: 'border-aj-approve/40 bg-aj-approve/10 text-aj-approve',
    info: 'border-aj-brand/40 bg-aj-brand/10 text-aj-brand',
    danger: 'border-aj-block/40 bg-aj-block/10 text-aj-block',
  }
  return (
    <div className={cn('flex items-start gap-2 rounded-xl border px-4 py-3 text-sm', styles[tone])}>
      <ShieldAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
      <div>{children}</div>
    </div>
  )
}
