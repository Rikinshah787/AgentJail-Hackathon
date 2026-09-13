export type Decision = 'allow' | 'block' | 'approval_required'

export type ApiSource = 'live' | 'demo'

export type RiskLevel = 'Low' | 'Medium' | 'High' | 'Critical'

export type NavId =
  | 'control-room'
  | 'live-demo'
  | 'breach-arena'
  | 'incidents'
  | 'approvals'
  | 'scars'
  | 'evaluations'
  | 'policies'
  | 'integrations'

export type DecisionCard = {
  id: string
  decision: Decision
  title: string
  reason: string
  tool: string
  risk: RiskLevel
  timeAgo: string
}

export type Incident = {
  id: string
  title: string
  decision: Decision
  risk: RiskLevel
  executed: boolean
  scenario?: string
  summary: string
  whatTried: string
  whyRisky: string
  whatDecided: string
  whatHappened: string
  nextStep: string
  timeline: {
    title: string
    detail: string
    checks?: { label: string; value: string; ok?: boolean }[]
  }[]
  technical: {
    actorId: string
    toolParams: Record<string, string>
    sourceMetadata: Record<string, string>
    policyId: string
    riskScore: number
    traceId: string
    latencyMs: number
  }
}

export type ApprovalRequest = {
  id: string
  action: string
  agent: string
  actor: string
  source: string
  verified: boolean
  resource: string
  risk: RiskLevel
  why: string
  expiresIn: string
  expiresAt?: string
  expired?: boolean
}

export type Scar = {
  id: string
  name: string
  status: 'Active' | 'Under review' | 'Expired'
  tools: string[]
  sources: string[]
  timesMatched: number
  created: string
  lastMatched: string
  reviewer: string
  expires: string
}

export type ImprovementMetrics = {
  attack_block_rate?: number
  scar_recall?: number
  benign_allow_rate?: number
  false_positive_rate?: number
  unique_variants?: number
  observed_matches?: number
  observed_false_positives?: number
}

export type ImprovementRun = {
  id: string
  status: 'running' | 'awaiting_human' | 'active' | 'rejected' | 'rolled_back'
  candidateScarId?: string
  iterations: number
  metrics: ImprovementMetrics
  monitorMetrics: ImprovementMetrics
  stopReason: string
  reviewer?: string
  reviewReason?: string
  variants: { rationale: string; model: string; model_powered: boolean; iteration: number }[]
  history: Record<string, unknown>[]
}

export type Policy = {
  id: string
  name: string
  plainEnglish: string
  appliesTo: string[]
  decision: 'Approval required' | 'Block' | 'Allow'
  advancedJson: string
}

export type DemoScenarioId = 'poisoned' | 'mutated' | 'legitimate'

export type DashboardSnapshot = {
  attacksBlocked: number
  safeAllowed: number
  awaitingApproval: number
  scarMatches: number
  recent: DecisionCard[]
  protectionActive: boolean
}

export type DemoCheck = {
  name: string
  status: string
  explanation?: string
}

export type DemoRunResult = {
  decision: Decision
  risk: RiskLevel
  reason: string
  executed: boolean
  matchedScar: boolean
  scarName?: string
  tool: string
  latencyMs?: number
  traceId?: string
  policyId?: string
  actorId?: string
  toolParams?: Record<string, string>
  sourceMetadata?: Record<string, string>
  checks: DemoCheck[]
  pendingId?: string
  incidentId?: string
  executorProvider?: string
  sandboxCreated?: boolean
  sandboxId?: string
  executionDurationMs?: number
  unprotectedSandboxId?: string
}

export type EvalSnapshot = {
  modes: { name: string; attackSuccess: number; taskCompletion: number; measured?: boolean; note?: string }[]
  attacksContained: number
  falsePositiveRate: number
  approvalRate: number
  scarRecall: number
  p95LatencyMs: number
  casesCompleted: number
  failures: number
  benchmarks: string[]
  honestClaims: string[]
  doNotClaim: string[]
  methodology?: string
  probePassed?: number
  probeTotal?: number
  injecHoldoutClaim?: string
  injecUnprotectedRate?: number
  injecJailRate?: number
}
