import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { api, Conflict } from '@/api/client'
import {
  AlertTriangle, Filter, CheckCircle, EyeOff,
  RefreshCw, ChevronDown, ChevronUp, GitMerge
} from 'lucide-react'
import { SeverityBadge } from '@/components/StatusBadge'
import { PageLoader } from '@/components/LoadingSpinner'
import EmptyState from '@/components/EmptyState'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

export default function ConflictsPage() {
  const qc = useQueryClient()
  const [severityFilter, setSeverityFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('open')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['conflicts', severityFilter, statusFilter],
    queryFn: () => api.getConflicts(severityFilter || undefined, statusFilter || undefined),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, status, note }: { id: string; status: string; note?: string }) =>
      api.updateConflict(id, status, note),
    onSuccess: () => {
      toast.success('Conflict status updated.')
      qc.invalidateQueries({ queryKey: ['conflicts'] })
    },
    onError: () => toast.error('Failed to update conflict.'),
  })

  const conflicts = data?.conflicts ?? []

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-sentinel-text">Conflict Dashboard</h2>
          <p className="text-sm text-sentinel-gray mt-0.5">
            Contradictions detected across uploaded documents
          </p>
        </div>
        <button onClick={() => refetch()} className="btn-secondary text-xs">
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4">
        <SummaryCard label="Total Conflicts" value={data?.total ?? 0} color="border-sentinel-border" textColor="text-sentinel-text" />
        <SummaryCard label="High Severity"   value={data?.high   ?? 0} color="border-red-500/30"    textColor="text-red-400" />
        <SummaryCard label="Medium Severity" value={data?.medium ?? 0} color="border-amber-500/30"  textColor="text-amber-400" />
        <SummaryCard label="Low Severity"    value={data?.low    ?? 0} color="border-blue-500/30"   textColor="text-blue-400" />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Filter className="w-4 h-4 text-sentinel-gray" />
        <select
          value={severityFilter}
          onChange={e => setSeverityFilter(e.target.value)}
          className="input-field py-1.5 px-3 text-xs w-36"
        >
          <option value="">All Severities</option>
          <option value="HIGH">HIGH</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="LOW">LOW</option>
        </select>
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="input-field py-1.5 px-3 text-xs w-36"
        >
          <option value="">All Statuses</option>
          <option value="open">Open</option>
          <option value="resolved">Resolved</option>
          <option value="ignored">Ignored</option>
        </select>
        {(severityFilter || statusFilter) && (
          <button
            onClick={() => { setSeverityFilter(''); setStatusFilter('') }}
            className="text-xs text-sentinel-gray hover:text-sentinel-text transition-colors"
          >
            Clear filters
          </button>
        )}
        <span className="ml-auto text-xs text-sentinel-gray">{conflicts.length} result(s)</span>
      </div>

      {/* Conflict list */}
      {isLoading ? (
        <PageLoader label="Loading conflicts..." />
      ) : conflicts.length === 0 ? (
        <EmptyState
          icon={GitMerge}
          title="No conflicts found"
          description={statusFilter === 'open'
            ? "No open conflicts detected. Upload more documents to begin analysis."
            : "No conflicts match the current filters."}
        />
      ) : (
        <div className="space-y-2">
          {conflicts.map(conflict => (
            <ConflictRow
              key={conflict.id}
              conflict={conflict}
              expanded={expandedId === conflict.id}
              onToggle={() => setExpandedId(expandedId === conflict.id ? null : conflict.id)}
              onResolve={() => updateMutation.mutate({ id: conflict.id, status: 'resolved' })}
              onIgnore={() => updateMutation.mutate({ id: conflict.id, status: 'ignored' })}
              onReopen={() => updateMutation.mutate({ id: conflict.id, status: 'open' })}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function SummaryCard({ label, value, color, textColor }: {
  label: string; value: number; color: string; textColor: string
}) {
  return (
    <div className={clsx('glass-card p-4 border', color)}>
      <div className={clsx('text-2xl font-bold', textColor)}>{value}</div>
      <div className="text-xs text-sentinel-gray mt-1">{label}</div>
    </div>
  )
}

function ConflictRow({ conflict, expanded, onToggle, onResolve, onIgnore, onReopen }: {
  conflict: Conflict
  expanded: boolean
  onToggle: () => void
  onResolve: () => void
  onIgnore: () => void
  onReopen: () => void
}) {
  const isResolved = conflict.status === 'resolved'
  const isIgnored  = conflict.status === 'ignored'

  return (
    <div className={clsx(
      'glass-card overflow-hidden transition-all duration-200',
      conflict.severity === 'HIGH'   && conflict.status === 'open' && 'border-red-500/20',
      conflict.severity === 'MEDIUM' && conflict.status === 'open' && 'border-amber-500/15',
      (isResolved || isIgnored) && 'opacity-60',
    )}>
      {/* Row header */}
      <div className="p-4 flex items-center gap-4">
        <AlertTriangle className={clsx('w-5 h-5 flex-shrink-0', {
          'text-red-400':    conflict.severity === 'HIGH',
          'text-amber-400':  conflict.severity === 'MEDIUM',
          'text-blue-400':   conflict.severity === 'LOW',
        })} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-bold text-sentinel-text uppercase tracking-wide">
              {conflict.field.replace(/_/g, ' ')}
            </span>
            <SeverityBadge severity={conflict.severity} />
            {(isResolved || isIgnored) && (
              <span className={clsx(
                'text-[10px] px-1.5 py-0.5 rounded font-medium',
                isResolved ? 'bg-sentinel-green/10 text-sentinel-green' : 'bg-sentinel-gray/10 text-sentinel-gray'
              )}>
                {isResolved ? 'RESOLVED' : 'IGNORED'}
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <span className="text-sentinel-gray">{conflict.document_a_name}: </span>
              <span className="text-sentinel-text font-mono font-medium">{conflict.value_a}</span>
            </div>
            <div>
              <span className="text-sentinel-gray">{conflict.document_b_name}: </span>
              <span className="text-sentinel-text font-mono font-medium">{conflict.value_b}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[10px] text-sentinel-gray">
            {formatDistanceToNow(new Date(conflict.created_at), { addSuffix: true })}
          </span>
          <button onClick={onToggle} className="p-1.5 rounded text-sentinel-gray hover:text-sentinel-text transition-colors">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-sentinel-border p-4 space-y-4 bg-sentinel-bg/30">
          {/* Side-by-side comparison */}
          <div>
            <p className="section-header mb-3">Document Comparison</p>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-sentinel-border p-3">
                <p className="text-[10px] text-sentinel-gray uppercase tracking-wide mb-1">Document A</p>
                <p className="text-xs font-semibold text-sentinel-cyan mb-2">{conflict.document_a_name}</p>
                <div className="bg-sentinel-bg rounded p-2">
                  <p className="text-sm font-bold text-sentinel-text font-mono">{conflict.value_a}</p>
                </div>
              </div>
              <div className="rounded-lg border border-sentinel-border p-3">
                <p className="text-[10px] text-sentinel-gray uppercase tracking-wide mb-1">Document B</p>
                <p className="text-xs font-semibold text-sentinel-cyan mb-2">{conflict.document_b_name}</p>
                <div className="bg-sentinel-bg rounded p-2">
                  <p className="text-sm font-bold text-sentinel-text font-mono">{conflict.value_b}</p>
                </div>
              </div>
            </div>
            <div className="mt-2 px-3 py-2 rounded-lg bg-amber-500/5 border border-amber-500/15">
              <p className="text-xs text-amber-300">
                ⚠ DocuSentinel does not select one value as correct.
                Both versions are presented for human review.
              </p>
            </div>
          </div>

          {/* Description */}
          {conflict.description && (
            <p className="text-xs text-sentinel-text-dim">{conflict.description}</p>
          )}

          {/* Actions */}
          {conflict.status === 'open' && (
            <div className="flex gap-2">
              <button onClick={onResolve} className="btn-secondary text-xs">
                <CheckCircle className="w-3.5 h-3.5" />
                Mark Resolved
              </button>
              <button onClick={onIgnore} className="btn-secondary text-xs">
                <EyeOff className="w-3.5 h-3.5" />
                Ignore
              </button>
            </div>
          )}
          {(isResolved || isIgnored) && (
            <button onClick={onReopen} className="btn-secondary text-xs">
              Reopen
            </button>
          )}
        </div>
      )}
    </div>
  )
}
