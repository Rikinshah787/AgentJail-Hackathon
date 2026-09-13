import { useState, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { ChevronDown, type LucideIcon } from 'lucide-react'
import { cn } from '../lib/utils'

export function Card({
  children,
  className,
  hover = false,
}: {
  children: ReactNode
  className?: string
  hover?: boolean
}) {
  return (
    <div
      className={cn(
        'rounded-xl border border-aj-border bg-aj-card shadow-none',
        hover && 'aj-card-hover',
        className,
      )}
    >
      {children}
    </div>
  )
}

export function MetricCard({
  icon: Icon,
  label,
  value,
  hint,
  tone = 'brand',
}: {
  icon: LucideIcon
  label: string
  value: string | number
  hint?: string
  tone?: 'brand' | 'allow' | 'block' | 'approve'
}) {
  const toneMap = {
    brand: 'text-aj-brand bg-aj-brand/15',
    allow: 'text-aj-allow bg-aj-allow/15',
    block: 'text-aj-block bg-aj-block/15',
    approve: 'text-aj-approve bg-aj-approve/15',
  }
  const bar = {
    brand: 'from-aj-brand/80 to-aj-brand/10',
    allow: 'from-aj-allow/80 to-aj-allow/10',
    block: 'from-aj-block/80 to-aj-block/10',
    approve: 'from-aj-approve/80 to-aj-approve/10',
  }
  return (
    <Card hover className="relative overflow-hidden p-5">
      <div className={cn('absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r', bar[tone])} />
      <div className="relative flex items-start justify-between gap-3">
        <div>
          <p className="text-sm text-aj-muted">{label}</p>
          <p className="mt-2 font-display text-3xl font-bold tracking-tight tabular-nums">{value}</p>
          {hint ? <p className="mt-2 text-xs text-aj-muted">{hint}</p> : null}
        </div>
        <span className={cn('rounded-xl p-2.5', toneMap[tone])}>
          <Icon className="size-5" aria-hidden />
        </span>
      </div>
    </Card>
  )
}

export function SectionTitle({
  title,
  subtitle,
  action,
}: {
  title: string
  subtitle?: string
  action?: ReactNode
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-3xl">
        <h2 className="font-display text-2xl font-bold tracking-tight md:text-[1.85rem]">{title}</h2>
        {subtitle ? <p className="mt-2 text-[15px] leading-relaxed text-aj-muted">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  )
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'allow' | 'approve'
  size?: 'sm' | 'md' | 'lg'
}) {
  const variants = {
    primary:
      'bg-aj-brand text-[#08101e] hover:bg-[#9abbff] shadow-none',
    secondary:
      'bg-white/[0.03] border border-aj-border text-aj-text hover:border-aj-brand/50 hover:bg-white/[0.06]',
    ghost: 'text-aj-muted hover:text-aj-text hover:bg-white/5',
    danger: 'bg-aj-block/90 text-white hover:bg-aj-block',
    allow: 'bg-aj-allow/90 text-aj-bg hover:bg-aj-allow',
    approve: 'bg-aj-approve/90 text-aj-bg hover:bg-aj-approve',
  }
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2.5 text-sm',
    lg: 'px-5 py-3 text-base',
  }
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition duration-150 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0',
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}

export function LoadingState({ label = 'Loading' }: { label?: string }) {
  return (
    <Card className="p-8 text-center">
      <p className="animate-pulse text-sm text-aj-muted" role="status" aria-live="polite">
        {label}…
      </p>
    </Card>
  )
}

export function EmptyState({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <Card className="p-8 text-center">
      <p className="font-display text-lg font-bold">{title}</p>
      {subtitle ? <p className="mt-2 text-sm leading-relaxed text-aj-muted">{subtitle}</p> : null}
    </Card>
  )
}

export function ErrorState({
  title = 'Something went wrong',
  message,
  details,
  onRetry,
}: {
  title?: string
  message: string
  details?: string
  onRetry?: () => void
}) {
  const [open, setOpen] = useState(false)
  return (
    <Card className="border-aj-block/35 bg-aj-block/[0.06] p-5">
      <p className="font-display text-lg font-bold text-aj-block">{title}</p>
      <p className="mt-1 text-sm leading-relaxed text-aj-muted">{message}</p>
      {details ? (
        <div className="mt-3">
          <button
            type="button"
            className="inline-flex items-center gap-1 text-sm font-semibold text-aj-brand"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
          >
            Technical details
            <ChevronDown className={cn('size-4 transition', open && 'rotate-180')} />
          </button>
          {open ? (
            <pre className="mt-3 overflow-x-auto rounded-xl border border-aj-border bg-aj-panel p-4 text-xs text-aj-muted">
              {details}
            </pre>
          ) : null}
        </div>
      ) : null}
      {onRetry ? (
        <Button className="mt-4" size="sm" variant="secondary" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </Card>
  )
}

export function ScenarioFailure({ details }: { details?: string }) {
  return (
    <ErrorState
      title="Scenario failed to complete"
      message="AgentJail did not finish this run, so no protection result is shown."
      details={details}
    />
  )
}
