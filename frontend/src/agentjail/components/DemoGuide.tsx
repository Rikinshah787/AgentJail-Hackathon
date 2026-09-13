import { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, RotateCcw, X } from 'lucide-react'
import { DEMO_SCENES } from '../data/mock'
import { Button, Card } from './ui'

export function DemoGuide({
  open,
  onClose,
  onJump,
  onReset,
}: {
  open: boolean
  onClose: () => void
  onJump: (scene: number) => void
  onReset: () => void
}) {
  const [step, setStep] = useState(0)
  const [showNotes, setShowNotes] = useState(false)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'n' || e.key === 'N') setShowNotes((v) => !v)
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowRight') setStep((s) => Math.min(DEMO_SCENES.length - 1, s + 1))
      if (e.key === 'ArrowLeft') setStep((s) => Math.max(0, s - 1))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  useEffect(() => {
    if (open) onJump(step + 1)
  }, [step, open, onJump])

  if (!open) return null

  const scene = DEMO_SCENES[step]

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 p-4 md:left-[232px]">
      <Card className="border-aj-brand/40 bg-aj-panel/96 p-4 shadow-[0_-12px_48px_rgba(0,0,0,0.5)] backdrop-blur-xl">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-aj-brand">
              Guided demo · Step {step + 1} of {DEMO_SCENES.length}
            </p>
            <h3 className="mt-1 font-display text-lg font-bold">{scene.title}</h3>
            <div className="mt-2 flex gap-1.5">
              {DEMO_SCENES.map((_, i) => (
                <span
                  key={i}
                  className={`h-1.5 w-8 rounded-full ${i === step ? 'bg-aj-brand' : i < step ? 'bg-aj-brand/40' : 'bg-aj-border'}`}
                />
              ))}
            </div>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-aj-muted hover:bg-white/5" aria-label="Close demo guide">
            <X className="size-4" />
          </button>
        </div>

        {showNotes ? (
          <p className="mt-3 rounded-xl border border-aj-border bg-aj-card px-3 py-2 text-sm text-aj-muted">
            <span className="font-semibold text-aj-text">Presenter note: </span>
            {scene.note}
          </p>
        ) : (
          <p className="mt-2 text-xs text-aj-muted">Press N for presenter notes · Esc to close</p>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="secondary" size="sm" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
            <ChevronLeft className="size-4" /> Previous
          </Button>
          <Button
            size="sm"
            disabled={step === DEMO_SCENES.length - 1}
            onClick={() => setStep((s) => s + 1)}
          >
            Next <ChevronRight className="size-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setStep(0)}>
            <RotateCcw className="size-4" /> Restart demo
          </Button>
          <Button variant="ghost" size="sm" onClick={onReset}>
            Reset demo data
          </Button>
        </div>
      </Card>
    </div>
  )
}
