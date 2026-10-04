import { CheckCircle, AlertTriangle, HelpCircle, XCircle } from 'lucide-react'
import clsx from 'clsx'

type AnswerStatus = 'VERIFIED' | 'CONFLICTING' | 'UNCERTAIN' | 'NOT_FOUND'
type ConflictSeverity = 'HIGH' | 'MEDIUM' | 'LOW'

export function AnswerStatusBadge({ status }: { status: AnswerStatus }) {
  const config = {
    VERIFIED:    { cls: 'badge-verified',    icon: CheckCircle,    label: 'Verified' },
    CONFLICTING: { cls: 'badge-conflicting', icon: AlertTriangle,  label: 'Conflicting' },
    UNCERTAIN:   { cls: 'badge-uncertain',   icon: HelpCircle,     label: 'Uncertain' },
    NOT_FOUND:   { cls: 'badge-not-found',   icon: XCircle,        label: 'Not Found' },
  }[status]

  const Icon = config.icon
  return (
    <span className={config.cls}>
      <Icon className="w-3 h-3" />
      {config.label}
    </span>
  )
}

export function SeverityBadge({ severity }: { severity: ConflictSeverity | string }) {
  const cls = {
    HIGH:   'badge-high',
    MEDIUM: 'badge-medium',
    LOW:    'badge-low',
  }[severity as ConflictSeverity] ?? 'badge-low'

  return <span className={cls}>{severity}</span>
}

export function DocumentStatusBadge({ status }: { status: string }) {
  const config: Record<string, { color: string; dot: string; label: string }> = {
    uploading:  { color: 'text-blue-400',   dot: 'bg-blue-400',    label: 'Uploading' },
    extracting: { color: 'text-amber-400',  dot: 'bg-amber-400',   label: 'Extracting' },
    indexing:   { color: 'text-purple-400', dot: 'bg-purple-400',  label: 'Indexing' },
    ready:      { color: 'text-green-400',  dot: 'bg-green-400',   label: 'Ready' },
    failed:     { color: 'text-red-400',    dot: 'bg-red-400',     label: 'Failed' },
  }
  const c = config[status] ?? config['failed']
  return (
    <span className={clsx('inline-flex items-center gap-1.5 text-xs font-medium', c.color)}>
      <span className={clsx('w-1.5 h-1.5 rounded-full', c.dot,
        status !== 'ready' && status !== 'failed' ? 'animate-pulse' : ''
      )} />
      {c.label}
    </span>
  )
}
