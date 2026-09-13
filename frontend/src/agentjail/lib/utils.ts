import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function timeAgo(iso?: string | null): string {
  if (!iso) return 'just now'
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return iso
  const delta = Date.now() - then
  if (delta < 15_000) return 'a few seconds ago'
  if (delta < 60_000) return `${Math.max(1, Math.round(delta / 1000))} seconds ago`
  if (delta < 3_600_000) return `${Math.max(1, Math.round(delta / 60_000))} minutes ago`
  if (delta < 86_400_000) return `${Math.max(1, Math.round(delta / 3_600_000))} hours ago`
  return `${Math.max(1, Math.round(delta / 86_400_000))} days ago`
}

export function expiresInLabel(iso?: string | null, fallback = '—'): string {
  if (!iso) return fallback
  const ms = new Date(iso).getTime() - Date.now()
  if (Number.isNaN(ms)) return fallback
  if (ms <= 0) return 'Expired'
  const total = Math.floor(ms / 1000)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

export function countdownLabel(label: string, startedAt: number, now: number): string {
  const match = /^(\d+):(\d+)$/.exec(label)
  if (!match) return label
  const remaining = Number(match[1]) * 60 + Number(match[2]) - Math.floor((now - startedAt) / 1000)
  if (remaining <= 0) return 'Expired'
  const m = Math.floor(remaining / 60)
  const s = remaining % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

export function titleCase(value: string): string {
  if (!value) return value
  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase()
}
