import { ExternalLink, Maximize2, Play, Shield } from 'lucide-react'
import { Button, Card, SectionTitle } from '../components/ui'

export function BreachArena() {
  return (
    <div className="space-y-5">
      <SectionTitle
        title="Breach Arena"
        subtitle="Cinematic 3D proof of the same AgentJail gate — best in a full browser tab with WebGL."
      />

      <Card className="relative overflow-hidden border-white/10 bg-gradient-to-br from-[#0a1024] via-[#121a33] to-aj-panel p-6 sm:p-8">
        <div className="pointer-events-none absolute -right-16 -top-20 size-64 rounded-full bg-aj-brand/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-24 left-10 size-56 rounded-full bg-[#ff3d61]/15 blur-3xl" />

        <div className="relative grid gap-6 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-aj-brand">3D proof layer</p>
            <h3 className="mt-3 font-display text-2xl font-extrabold tracking-tight sm:text-3xl">
              Runtime firewall for autonomous SRE agents
            </h3>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-aj-muted sm:text-base">
              Act 1 shows the breach without a gate. Act 2 blocks the same attack. Act 3 stops the mutated replay and
              allows a signed restart. Same backend decisions as Live Demo — visualized.
            </p>
            <div className="mt-6 flex flex-wrap gap-2.5">
              <Button
                size="lg"
                onClick={() => window.open('/arena', '_blank', 'noopener,noreferrer')}
              >
                <Play className="size-4" /> Launch Breach Arena
              </Button>
              <a
                href="/arena"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-xl border border-aj-border bg-aj-card/80 px-4 py-2.5 text-sm font-medium text-aj-text hover:border-aj-brand/40"
              >
                <Maximize2 className="size-4" />
                Open fullscreen
                <ExternalLink className="size-3.5 text-aj-muted" />
              </a>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/35 p-5">
            <div className="flex items-center gap-2 text-aj-brand">
              <Shield className="size-4" aria-hidden />
              <p className="text-xs font-semibold uppercase tracking-wider">Demo script</p>
            </div>
            <ol className="mt-3 space-y-2.5 text-sm text-aj-muted">
              <li>
                <span className="font-semibold text-aj-text">1.</span> Attack wins (no firewall)
              </li>
              <li>
                <span className="font-semibold text-aj-text">2.</span> Jail blocks + scar
              </li>
              <li>
                <span className="font-semibold text-aj-text">3.</span> Replay denied · legit restart allowed
              </li>
              <li>
                <span className="font-semibold text-aj-text">4.</span> Ask ARIA / open Weave
              </li>
            </ol>
            <p className="mt-4 text-xs leading-relaxed text-aj-muted">
              Tip: use Chrome/Edge. Embedded WebGL previews often look blank (white + banner only).
            </p>
          </div>
        </div>
      </Card>

      <p className="text-sm text-aj-muted">
        Product home stays at <code className="text-aj-text">/ariai-logic</code>. Arena is the movie; Control Room +
        Live Demo are the proof with live API data.
      </p>
    </div>
  )
}
