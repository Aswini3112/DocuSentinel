import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import {
  FileText, AlertTriangle, CheckCircle, HelpCircle,
  Search, TrendingUp, Shield, Zap, ChevronRight,
  Clock, Database
} from 'lucide-react'
import { AnswerStatusBadge, SeverityBadge } from '@/components/StatusBadge'
import { PageLoader } from '@/components/LoadingSpinner'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

export default function DashboardPage() {
  const navigate = useNavigate()

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.getStats(),
    refetchInterval: 15_000,
  })

  const { data: investigationsData } = useQuery({
    queryKey: ['investigations', 5],
    queryFn: () => api.getInvestigations(5),
  })

  const { data: conflictsData } = useQuery({
    queryKey: ['conflicts'],
    queryFn: () => api.getConflicts(),
  })

  const { data: docsData } = useQuery({
    queryKey: ['documents'],
    queryFn: () => api.getDocuments(),
  })

  if (statsLoading) return <PageLoader label="Loading dashboard..." />

  const recentInvestigations = investigationsData?.investigations ?? []
  const recentConflicts = (conflictsData?.conflicts ?? []).slice(0, 4)
  const recentDocs = (docsData?.documents ?? []).slice(0, 5)

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Page Title */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-sentinel-text">Intelligence Dashboard</h2>
          <p className="text-sm text-sentinel-gray mt-0.5">
            Evidence-first AI document investigation
          </p>
        </div>
        <button
          onClick={() => navigate('/documents')}
          className="btn-primary"
        >
          <FileText className="w-4 h-4" />
          Upload Documents
        </button>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          icon={FileText}
          value={stats?.documents_analyzed ?? 0}
          label="Documents Analyzed"
          color="cyan"
          onClick={() => navigate('/documents')}
        />
        <StatCard
          icon={Database}
          value={stats?.claims_extracted ?? 0}
          label="Claims Extracted"
          color="blue"
        />
        <StatCard
          icon={AlertTriangle}
          value={stats?.conflicts_detected ?? 0}
          label="Conflicts Detected"
          color="amber"
          onClick={() => navigate('/conflicts')}
        />
        <StatCard
          icon={HelpCircle}
          value={stats?.uncertain_claims ?? 0}
          label="Uncertain Claims"
          color="purple"
        />
        <StatCard
          icon={CheckCircle}
          value={`${stats?.evidence_coverage ?? 0}%`}
          label="Evidence Coverage"
          color="green"
        />
      </div>

      {/* Investigation Health */}
      <div className="glass-card p-5">
        <div className="section-header">Investigation Health</div>
        <div className="grid grid-cols-3 gap-6">
          <HealthMetric
            label="Evidence Coverage"
            value={stats?.evidence_coverage ?? 0}
            description="% of questions with supporting evidence"
          />
          <HealthMetric
            label="Answer Confidence"
            value={stats?.answer_confidence ?? 0}
            description="Average confidence across investigations"
          />
          <HealthMetric
            label="Conflict Risk"
            value={stats?.conflict_risk ?? 0}
            description="% of investigations with detected conflicts"
            invert
          />
        </div>
      </div>

      {/* Three-column lower section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Recent Investigations */}
        <div className="glass-card p-5 lg:col-span-1">
          <div className="section-header">Recent Investigations</div>
          {recentInvestigations.length === 0 ? (
            <p className="text-sm text-sentinel-gray py-4 text-center">
              No investigations yet. Start by asking a question.
            </p>
          ) : (
            <div className="space-y-2">
              {recentInvestigations.map(inv => (
                <button
                  key={inv.id}
                  onClick={() => navigate('/investigate')}
                  className="w-full text-left p-3 rounded-lg bg-sentinel-bg/50 border border-sentinel-border hover:border-sentinel-border-bright transition-all group"
                >
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <p className="text-xs text-sentinel-text leading-snug line-clamp-2 flex-1">
                      {inv.question}
                    </p>
                    <ChevronRight className="w-3 h-3 text-sentinel-gray flex-shrink-0 mt-0.5 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                  <div className="flex items-center gap-2">
                    <AnswerStatusBadge status={inv.answer_status as any} />
                    <span className="text-[10px] text-sentinel-gray ml-auto">
                      {formatDistanceToNow(new Date(inv.created_at), { addSuffix: true })}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
          <button
            onClick={() => navigate('/investigate')}
            className="w-full mt-3 btn-secondary text-xs justify-center"
          >
            <Search className="w-3.5 h-3.5" />
            New Investigation
          </button>
        </div>

        {/* Recent Conflicts */}
        <div className="glass-card p-5 lg:col-span-1">
          <div className="section-header">Recent Conflicts</div>
          {recentConflicts.length === 0 ? (
            <p className="text-sm text-sentinel-gray py-4 text-center">
              No conflicts detected yet.
            </p>
          ) : (
            <div className="space-y-2">
              {recentConflicts.map(c => (
                <div
                  key={c.id}
                  className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/15"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-semibold text-amber-400 uppercase tracking-wide">
                      {c.field.replace('_', ' ')}
                    </span>
                    <SeverityBadge severity={c.severity} />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <p className="text-[10px] text-sentinel-gray mb-0.5">{c.document_a_name}</p>
                      <p className="text-xs text-sentinel-text font-mono truncate">{c.value_a}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-sentinel-gray mb-0.5">{c.document_b_name}</p>
                      <p className="text-xs text-sentinel-text font-mono truncate">{c.value_b}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          <button
            onClick={() => navigate('/conflicts')}
            className="w-full mt-3 btn-secondary text-xs justify-center"
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            View All Conflicts
          </button>
        </div>

        {/* Document Activity */}
        <div className="glass-card p-5 lg:col-span-1">
          <div className="section-header">Document Activity</div>
          {recentDocs.length === 0 ? (
            <p className="text-sm text-sentinel-gray py-4 text-center">
              No documents uploaded yet.
            </p>
          ) : (
            <div className="space-y-2">
              {recentDocs.map(doc => (
                <div key={doc.id} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-sentinel-border/30 transition-colors">
                  <div className="w-8 h-8 rounded-md bg-sentinel-cyan/10 border border-sentinel-cyan/20 flex items-center justify-center flex-shrink-0">
                    <span className="text-[9px] font-bold text-sentinel-cyan">{doc.file_type}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-sentinel-text truncate">{doc.original_name}</p>
                    <p className="text-[10px] text-sentinel-gray">
                      {doc.status === 'ready'
                        ? `${doc.page_count}p · ${doc.chunk_count} chunks`
                        : doc.status}
                    </p>
                  </div>
                  <div className={clsx('w-1.5 h-1.5 rounded-full flex-shrink-0', {
                    'bg-sentinel-green': doc.status === 'ready',
                    'bg-sentinel-amber animate-pulse': ['uploading','extracting','indexing'].includes(doc.status),
                    'bg-red-400': doc.status === 'failed',
                  })} />
                </div>
              ))}
            </div>
          )}
          <button
            onClick={() => navigate('/documents')}
            className="w-full mt-3 btn-secondary text-xs justify-center"
          >
            <FileText className="w-3.5 h-3.5" />
            Manage Documents
          </button>
        </div>
      </div>
    </div>
  )
}

function StatCard({
  icon: Icon, value, label, color, onClick
}: {
  icon: any; value: number | string; label: string
  color: 'cyan' | 'blue' | 'amber' | 'purple' | 'green'
  onClick?: () => void
}) {
  const colorMap = {
    cyan:   { bg: 'bg-sentinel-cyan/10',   border: 'border-sentinel-cyan/20',   text: 'text-sentinel-cyan' },
    blue:   { bg: 'bg-blue-500/10',        border: 'border-blue-500/20',        text: 'text-blue-400' },
    amber:  { bg: 'bg-amber-500/10',       border: 'border-amber-500/20',       text: 'text-amber-400' },
    purple: { bg: 'bg-purple-500/10',      border: 'border-purple-500/20',      text: 'text-purple-400' },
    green:  { bg: 'bg-emerald-500/10',     border: 'border-emerald-500/20',     text: 'text-emerald-400' },
  }[color]

  return (
    <div
      onClick={onClick}
      className={clsx(
        'stat-card',
        onClick && 'cursor-pointer hover:border-sentinel-border-bright transition-all hover:-translate-y-0.5'
      )}
    >
      <div className={clsx('w-9 h-9 rounded-lg flex items-center justify-center border', colorMap.bg, colorMap.border)}>
        <Icon className={clsx('w-4 h-4', colorMap.text)} />
      </div>
      <div>
        <div className={clsx('text-2xl font-bold', colorMap.text)}>{value}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  )
}

function HealthMetric({ label, value, description, invert = false }: {
  label: string; value: number; description: string; invert?: boolean
}) {
  const pct = Math.round(value)
  const isGood = invert ? pct < 30 : pct >= 60
  const isMid  = invert ? pct < 60 : pct >= 30
  const color = isGood ? 'text-sentinel-green' : isMid ? 'text-sentinel-amber' : 'text-red-400'
  const bar = isGood ? 'bg-sentinel-green' : isMid ? 'bg-sentinel-amber' : 'bg-red-400'

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-sentinel-text">{label}</span>
        <span className={clsx('text-sm font-bold font-mono', color)}>{pct}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-sentinel-border overflow-hidden">
        <div className={clsx('h-full rounded-full transition-all duration-700', bar)}
          style={{ width: `${pct}%` }} />
      </div>
      <p className="text-[11px] text-sentinel-gray">{description}</p>
    </div>
  )
}
