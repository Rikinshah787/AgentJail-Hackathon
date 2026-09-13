import type {
  ApprovalRequest,
  DecisionCard,
  Incident,
  Policy,
  Scar,
} from '../types'

export const DEMO_METRICS = {
  attacksBlocked: 8,
  safeAllowed: 8,
  awaitingApproval: 10,
  scarMatches: 8,
  label: 'Demo results',
}

export const PROTECTED_AGENTS = ['SRE Agent', 'Ops Copilot', 'Support Agent'] as const

export const RECENT_DECISIONS: DecisionCard[] = [
  {
    id: 'd1',
    decision: 'block',
    title: 'Unverified ticket attempted to create an administrator identity.',
    reason: 'The request came from an unverified source.',
    tool: 'create_service_identity',
    risk: 'Critical',
    timeAgo: '20 seconds ago',
  },
  {
    id: 'd2',
    decision: 'allow',
    title: 'Verified monitoring alert requested a safe service restart.',
    reason: 'Verified source and limited blast radius.',
    tool: 'restart_service',
    risk: 'Low',
    timeAgo: '2 minutes ago',
  },
  {
    id: 'd3',
    decision: 'approval_required',
    title: 'Verified operator requested a privileged identity.',
    reason: 'Identity creation always requires a human.',
    tool: 'create_service_identity',
    risk: 'High',
    timeAgo: '5 minutes ago',
  },
]

export const INCIDENTS: Incident[] = [
  {
    id: 'inc-001',
    title: 'Critical incident — Privileged identity creation blocked',
    decision: 'block',
    risk: 'Critical',
    executed: false,
    summary: 'No external action occurred.',
    whatTried: 'The agent tried to create an administrator service identity.',
    whyRisky:
      'The instruction came from an unverified incident ticket and asked for elevated privileges.',
    whatDecided: 'AgentJail blocked the action before execution.',
    whatHappened: 'No infrastructure change occurred.',
    nextStep: 'Review the ticket source, then update policy or mark as reviewed.',
    timeline: [
      {
        title: 'Source content received',
        detail: 'Incident ticket was not cryptographically verified.',
      },
      {
        title: 'Agent action proposed',
        detail: 'create_service_identity',
      },
      {
        title: 'Authorization checks',
        detail: 'Multiple checks failed before execution.',
        checks: [
          { label: 'Source verification', value: 'Failed', ok: false },
          { label: 'Actor permission', value: 'Insufficient', ok: false },
          { label: 'Tool sensitivity', value: 'Critical', ok: false },
          { label: 'Scar match', value: 'Yes', ok: false },
          { label: 'Human approval', value: 'Missing', ok: false },
        ],
      },
      {
        title: 'Final decision',
        detail: 'Blocked before execution',
      },
      {
        title: 'Evidence recorded',
        detail: 'Complete decision trace saved to Weave',
      },
    ],
    technical: {
      actorId: 'sre-agent-01',
      toolParams: {
        role: 'administrator',
        name: 'temporary-ops-admin',
        ttl: '1h',
      },
      sourceMetadata: {
        type: 'incident-ticket',
        id: 'INC-4821',
        verified: 'false',
      },
      policyId: 'pol-privileged-identity',
      riskScore: 0.94,
      traceId: 'tr_aj_7f3a91c2',
      latencyMs: 18,
    },
  },
]

export const APPROVALS: ApprovalRequest[] = [
  {
    id: 'ap-1',
    action: 'Create privileged service identity',
    agent: 'SRE Agent',
    actor: 'Verified operator · jordan@acme.io',
    source: 'Slack #ops-escalation',
    verified: true,
    resource: 'iam://service-accounts/ops-admin',
    risk: 'High',
    why: 'Identity creation is too sensitive for an agent to execute alone.',
    expiresIn: '14:32',
  },
  {
    id: 'ap-2',
    action: 'Grant temporary cluster-admin binding',
    agent: 'Ops Copilot',
    actor: 'System · pagerduty-escalation',
    source: 'PagerDuty incident PD-9912',
    verified: true,
    resource: 'k8s://cluster-role-binding/temp-admin',
    risk: 'Critical',
    why: 'Cluster-admin changes always need a human checkpoint.',
    expiresIn: '08:05',
  },
  {
    id: 'ap-3',
    action: 'Export customer PII for support case',
    agent: 'Support Agent',
    actor: 'Human · alex@acme.io',
    source: 'Zendesk ticket ZD-2201',
    verified: true,
    resource: 'crm://customers/export',
    risk: 'High',
    why: 'Private customer data leaves the system only with approval.',
    expiresIn: '22:18',
  },
]

export const SCARS: Scar[] = [
  {
    id: 'scar-1',
    name: 'Unverified privilege escalation',
    status: 'Active',
    tools: ['create_service_identity', 'grant_admin_role'],
    sources: ['incident-ticket', 'email'],
    timesMatched: 8,
    created: '2026-09-12',
    lastMatched: '20 seconds ago',
    reviewer: 'Security on-call',
    expires: '2026-12-12',
  },
  {
    id: 'scar-2',
    name: 'Urgent refund hijack',
    status: 'Under review',
    tools: ['transfer_funds', 'issue_refund'],
    sources: ['support-ticket', 'chat'],
    timesMatched: 3,
    created: '2026-09-10',
    lastMatched: '1 day ago',
    reviewer: 'Fraud review',
    expires: '2026-11-10',
  },
  {
    id: 'scar-3',
    name: 'Hidden exfil via summary email',
    status: 'Expired',
    tools: ['send_email', 'export_document'],
    sources: ['document', 'website'],
    timesMatched: 2,
    created: '2026-06-01',
    lastMatched: '45 days ago',
    reviewer: 'DLP team',
    expires: '2026-09-01',
  },
]

export const POLICIES: Policy[] = [
  {
    id: 'pol-1',
    name: 'Privileged identity protection',
    plainEnglish:
      'If an agent tries to create a privileged identity, require a verified source and human approval.',
    appliesTo: ['create_service_identity', 'grant_admin_role', 'create_api_key'],
    decision: 'Approval required',
    advancedJson: `{
  "id": "pol-privileged-identity",
  "when": {
    "tools": ["create_service_identity", "grant_admin_role", "create_api_key"],
    "role_contains": ["admin", "privileged"]
  },
  "require": {
    "source_verified": true,
    "human_approval": true
  },
  "else": "block"
}`,
  },
  {
    id: 'pol-2',
    name: 'Unverified source block',
    plainEnglish:
      'If the instruction came from an unverified ticket, email, or website, block high-risk tools.',
    appliesTo: ['create_service_identity', 'transfer_funds', 'modify_firewall'],
    decision: 'Block',
    advancedJson: `{
  "id": "pol-unverified-source",
  "when": { "source_verified": false, "risk": ["High", "Critical"] },
  "decision": "block"
}`,
  },
  {
    id: 'pol-3',
    name: 'Safe restart allowlist',
    plainEnglish:
      'Allow verified monitoring systems to restart known services with limited blast radius.',
    appliesTo: ['restart_service'],
    decision: 'Allow',
    advancedJson: `{
  "id": "pol-safe-restart",
  "when": {
    "tool": "restart_service",
    "source_verified": true,
    "resource_in_allowlist": true
  },
  "decision": "allow"
}`,
  },
]

export const EVAL_MODES = [
  { name: 'Unprotected agent', attackSuccess: 86, taskCompletion: 92 },
  { name: 'Static rules', attackSuccess: 41, taskCompletion: 78 },
  { name: 'AgentJail without scars', attackSuccess: 18, taskCompletion: 88 },
  { name: 'AgentJail with scars', attackSuccess: 7, taskCompletion: 90 },
]

export const EVAL_SECONDARY = {
  attacksContained: 93,
  falsePositiveRate: 4.2,
  approvalRate: 12,
  scarRecall: 88,
  p95LatencyMs: 24,
  casesCompleted: 214,
  failures: 11,
}

export const EVAL_BENCHMARKS = [
  'Internal scenarios',
  'InjecAgent',
  'Clean benign controls',
  'Modern MCP attacks',
]

export const DEMO_SCENES = [
  {
    id: 1,
    title: 'Unprotected breach',
    note: 'Show the left panel first: without AgentJail the poisoned ticket creates an admin identity.',
  },
  {
    id: 2,
    title: 'AgentJail blocks attack',
    note: 'Run the protected path. Emphasize: unverified source + privileged tool → blocked. Nothing executed.',
  },
  {
    id: 3,
    title: 'Scar recognizes paraphrase',
    note: 'Switch to mutated scenario. Different words, same pattern. Scar match raised risk; policy decided.',
  },
  {
    id: 4,
    title: 'Human approval path',
    note: 'Show legitimate privileged request. Verified operator still needs Approve once — not permanent access.',
  },
] as const
