import { useState, useRef } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { api, InvestigateResponse } from '@/api/client'
import {
  Search, AlertTriangle, ChevronRight,
  FileText, Shield, AlertCircle, CheckCircle, Info
} from 'lucide-react'
import { AnswerStatusBadge, SeverityBadge } from '@/components/StatusBadge'
import ConfidenceBar from '@/components/ConfidenceBar'
import EmptyState from '@/components/EmptyState'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

const SUGGESTED_QUESTIONS = [
  'What is the project deadline?',
  'What is the total contract value?',
  'Who is the project manager?',
  'What is the late payment penalty rate?',
  'What is the late delivery penalty?',
  'Do all documents agree on the deadline?',
  'What modules are included in the project?',
  'What is the governing law of this contract?',
  "What is the company's GST number?",
]

export default function InvestigatePage() {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState<InvestigateResponse | null>(null)
  const [activeTab, setActiveTab] = useState<'answer' | 'evidence' | 'sources' | 'conflicts'>('answer')

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.getHealth(),
    refetchInterval: 30_000,
  })

  const { data: history } = useQuery({
    queryKey: ['investigations', 10],
    queryFn: () => api.getInvestigations(10),
  })

  const investigateMutation = useMutation({
    mutationFn: (q: string) => api.investigate(q),
    onSuccess: (data) => {
      setResult(data)
      setActiveTab('answer')
      if (data.has_conflict) {
        toast.custom(() => (
          <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/30 rounded-lg px-4 py-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span className="text-sm text-amber-300">Contradiction detected across documents</span>
          </div>
        ), { duration: 4000 })
      }
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Investigation failed. Check backend connection.')
    },
  })

  const handleSubmit = (q?: string) => {
    const text = (q || question).trim()
    if (!text) return
    setQuestion(text)
    investigateMutation.mutate(text)
  }

  const tabs = [
  { id: 'answer',    label: 'Answer',    count: null, alert: false },
  { id: 'evidence',  label: 'Evidence', count: result?.evidence.length, alert: false },
  { id: 'sources',   label: 'Sources',  count: result?.sources.length, alert: false },
  {
    id: 'conflicts',
    label: 'Conflicts',
    count: result?.conflicts.length,
    alert: result?.has_conflict ?? false,
  },
] as const

  const llmConfigured = health?.llm_status === 'CONFIGURED'

  return (
    <div className="space-y-5 animate-slide-up">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-bold text-sentinel-text">Investigation Workspace</h2>
          <p className="text-sm text-sentinel-gray mt-0.5">
            Ask questions — get evidence-backed answers with source traceability
          </p>
        </div>
        {/* Live AI status badge */}
        <div className={clsx(
          'flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium',
          llmConfigured
            ? 'bg-sentinel-green/10 border-sentinel-green/20 text-sentinel-green'
            : 'bg-sentinel-amber/10 border-sentinel-amber/20 text-sentinel-amber'
        )}>
          {llmConfigured
            ? <><CheckCircle className="w-3.5 h-3.5" /> AI Online — {health?.llm_model}</>
            : <><AlertCircle className="w-3.5 h-3.5" /> AI Not Configured</>
          }
        </div>
      </div>

      {/* NOT_CONFIGURED banner — shown before first investigation if LLM is absent */}
      {!llmConfigured && (
        <div className="flex items-start gap-3 p-4 rounded-lg border border-sentinel-amber/25 bg-sentinel-amber/5">
          <Info className="w-4 h-4 text-sentinel-amber flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-sentinel-amber">Evidence-Only Mode</p>
            <p className="text-xs text-sentinel-text-dim mt-0.5 leading-relaxed">
              No LLM API key is configured. Answers are built directly from retrieved document evidence —
              no AI reasoning, no hallucination. To enable full AI answers, add{' '}
              <code className="font-mono bg-sentinel-border px-1 rounded text-sentinel-cyan">LLM_API_KEY</code>{' '}
              to <code className="font-mono bg-sentinel-border px-1 rounded text-sentinel-cyan">backend/.env</code>.{' '}
              Get a free key at{' '}
              <a href="https://console.groq.com" target="_blank" rel="noopener noreferrer"
                className="text-sentinel-cyan hover:underline">console.groq.com</a>.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Left: Input + History */}
        <div className="xl:col-span-1 space-y-4">
          <div className="glass-card p-4 space-y-3">
            <p className="section-header">Ask a Question</p>
            <textarea
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit() }}
              placeholder="What is the project deadline across all documents?"
              rows={4}
              className="input-field resize-none text-sm"
            />
            <button
              onClick={() => handleSubmit()}
              disabled={!question.trim() || investigateMutation.isPending}
              className="btn-primary w-full justify-center"
            >
              {investigateMutation.isPending ? (
                <><div className="w-4 h-4 border-2 border-sentinel-bg border-t-transparent rounded-full animate-spin" /> Investigating…</>
              ) : (
                <><Search className="w-4 h-4" /> Investigate</>
              )}
            </button>
          </div>

          {/* Suggested questions */}
          <div className="glass-card p-4">
            <p className="section-header">Suggested Questions</p>
            <div className="space-y-0.5">
              {SUGGESTED_QUESTIONS.map(q => (
                <button
                  key={q}
                  onClick={() => { setQuestion(q); handleSubmit(q) }}
                  className="w-full text-left text-xs text-sentinel-gray hover:text-sentinel-text px-2 py-1.5 rounded hover:bg-sentinel-border/50 transition-colors flex items-start gap-1.5"
                >
                  <ChevronRight className="w-3 h-3 mt-0.5 flex-shrink-0 text-sentinel-cyan" />
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* History */}
          {(history?.investigations ?? []).length > 0 && (
            <div className="glass-card p-4">
              <p className="section-header">History</p>
              <div className="space-y-1.5">
                {history!.investigations.map(inv => (
                  <button
                    key={inv.id}
                    onClick={async () => {
                      const full = await api.getInvestigation(inv.id)
                      setResult(full); setQuestion(full.question); setActiveTab('answer')
                    }}
                    className="w-full text-left p-2 rounded hover:bg-sentinel-border/50 transition-colors"
                  >
                    <p className="text-xs text-sentinel-text line-clamp-1">{inv.question}</p>
                    <div className="flex items-center gap-1.5 mt-1">
                      <AnswerStatusBadge status={inv.answer_status as any} />
                      <span className="text-[10px] text-sentinel-gray ml-auto">
                        {formatDistanceToNow(new Date(inv.created_at), { addSuffix: true })}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: Result panel */}
        <div className="xl:col-span-3">
          {investigateMutation.isPending ? (
            <div className="glass-card p-10 flex flex-col items-center justify-center gap-4">
              <div className="relative w-16 h-16">
                <div className="absolute inset-0 border-2 border-sentinel-border rounded-full" />
                <div className="absolute inset-0 border-2 border-t-sentinel-cyan rounded-full animate-spin" />
                <Shield className="absolute inset-0 m-auto w-6 h-6 text-sentinel-cyan" />
              </div>
              <div className="text-center">
                <p className="text-sm font-semibold text-sentinel-text">Investigating…</p>
                <p className="text-xs text-sentinel-gray mt-1">Retrieving evidence · Detecting conflicts · Analyzing…</p>
              </div>
            </div>
          ) : result ? (
            <div className="space-y-4 animate-slide-up">
              {/* Status header */}
              <div className="glass-card p-5">
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div className="flex-1">
                    <p className="text-xs text-sentinel-gray mb-1">Question</p>
                    <p className="text-sm font-semibold text-sentinel-text">{result.question}</p>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <AnswerStatusBadge status={result.answer_status} />
                    {/* Show whether LLM was used for this result */}
                    <span className={clsx(
                      'text-[10px] px-2 py-0.5 rounded-full border font-medium',
                      result.llm_used
                        ? 'bg-sentinel-green/10 border-sentinel-green/20 text-sentinel-green'
                        : 'bg-sentinel-amber/10 border-sentinel-amber/20 text-sentinel-amber'
                    )}>
                      {result.llm_used ? '✓ AI Reasoning' : 'Evidence Only'}
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <ConfidenceBar percent={result.confidence_percent} reason={result.confidence_reason} size="sm" />
                  <div>
                    <p className="text-xs text-sentinel-gray mb-1">Evidence Strength</p>
                    <p className={clsx('text-sm font-semibold', {
                      'text-sentinel-green': result.evidence_strength === 'High',
                      'text-sentinel-amber': result.evidence_strength === 'Medium',
                      'text-red-400':        result.evidence_strength === 'Low',
                      'text-sentinel-gray':  result.evidence_strength === 'None',
                    })}>{result.evidence_strength}</p>
                  </div>
                  <div>
                    <p className="text-xs text-sentinel-gray mb-1">Sources</p>
                    <p className="text-sm font-semibold text-sentinel-text">{result.sources.length} document(s)</p>
                  </div>
                </div>
              </div>

              {/* Conflict banner */}
              {result.has_conflict && (
                <div className="flex items-start gap-3 p-4 rounded-lg border border-amber-500/25 bg-amber-500/5">
                  <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold text-amber-300">⚠ Contradiction Detected</p>
                    <p className="text-xs text-amber-200/70 mt-0.5">
                      The uploaded documents disagree on one or more facts. DocuSentinel does NOT
                      select one value as correct — review the Conflicts tab for full comparison.
                    </p>
                  </div>
                </div>
              )}

              {/* Tabs */}
              <div className="glass-card overflow-hidden">
                <div className="flex border-b border-sentinel-border">
                  {tabs.map(tab => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={clsx(
                        'px-4 py-3 text-sm font-medium transition-colors flex items-center gap-1.5',
                        activeTab === tab.id
                          ? 'text-sentinel-cyan border-b-2 border-sentinel-cyan -mb-px'
                          : 'text-sentinel-gray hover:text-sentinel-text'
                      )}
                    >
                      {tab.label}
                      {tab.count != null && tab.count > 0 && (
                        <span className={clsx(
                          'text-[10px] px-1.5 py-0.5 rounded-full font-bold',
                          tab.alert ? 'bg-amber-500/20 text-amber-400' : 'bg-sentinel-border text-sentinel-gray'
                        )}>
                          {tab.count}
                        </span>
                      )}
                    </button>
                  ))}
                </div>

                <div className="p-5">
                  {activeTab === 'answer' && (
                    <div>
                      {/* LLM not configured notice inline */}
                      {!result.llm_used && (
                        <div className="flex items-center gap-2 p-2.5 mb-4 rounded-lg bg-sentinel-amber/5 border border-sentinel-amber/20">
                          <Info className="w-3.5 h-3.5 text-sentinel-amber flex-shrink-0" />
                          <p className="text-xs text-sentinel-amber">
                            Evidence-only mode — no AI key configured. Answer shows retrieved document excerpts.
                          </p>
                        </div>
                      )}
                      <p className="text-sm text-sentinel-text leading-relaxed whitespace-pre-wrap font-mono text-xs">
                        {result.answer}
                      </p>
                    </div>
                  )}

                  {activeTab === 'evidence' && (
                    <div className="space-y-3">
                      {result.evidence.length === 0 ? (
                        <p className="text-sm text-sentinel-gray text-center py-6">No evidence retrieved for this question.</p>
                      ) : result.evidence.map((item, i) => (
                        <div key={item.chunk_id} className="p-3 rounded-lg bg-sentinel-bg/50 border border-sentinel-border">
                          <div className="flex items-center gap-2 mb-2 flex-wrap">
                            <span className="text-xs text-sentinel-cyan font-mono font-bold">#{i + 1}</span>
                            <span className="text-xs font-semibold text-sentinel-text">{item.document_name}</span>
                            <span className="text-xs text-sentinel-gray">· Page {item.page_number}</span>
                            {item.section && <span className="text-xs text-sentinel-gray">· {item.section}</span>}
                            <span className={clsx('ml-auto text-xs font-mono font-bold', {
                              'text-sentinel-green': item.relevance_score >= 0.6,
                              'text-sentinel-amber': item.relevance_score >= 0.3,
                              'text-sentinel-gray':  item.relevance_score < 0.3,
                            })}>
                              {(item.relevance_score * 100).toFixed(0)}% match
                            </span>
                          </div>
                          <p className="text-xs text-sentinel-text-dim leading-relaxed">{item.text}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {activeTab === 'sources' && (
                    <div className="space-y-2">
                      {result.sources.length === 0 ? (
                        <p className="text-sm text-sentinel-gray text-center py-6">No sources found.</p>
                      ) : result.sources.map((src, i) => (
                        <div key={i} className="p-3 rounded-lg border border-sentinel-border flex gap-3">
                          <div className="w-9 h-9 rounded-lg bg-sentinel-cyan/10 border border-sentinel-cyan/20 flex items-center justify-center flex-shrink-0">
                            <FileText className="w-4 h-4 text-sentinel-cyan" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-semibold text-sentinel-text">{src.document_name}</p>
                            <p className="text-xs text-sentinel-gray">
                              Page {src.page_number}{src.section ? ` · ${src.section}` : ''}
                            </p>
                            <p className="text-xs text-sentinel-text-dim mt-1.5 italic leading-relaxed">
                              "{src.excerpt.length > 200 ? src.excerpt.slice(0, 200) + '…' : src.excerpt}"
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {activeTab === 'conflicts' && (
                    <div className="space-y-3">
                      {result.conflicts.length === 0 ? (
                        <div className="flex items-center gap-2 p-3 rounded-lg bg-sentinel-green/5 border border-sentinel-green/20">
                          <Shield className="w-4 h-4 text-sentinel-green" />
                          <p className="text-sm text-sentinel-green">No conflicts detected — sources are consistent.</p>
                        </div>
                      ) : (
                        <>
                          <p className="text-xs text-sentinel-gray">
                            {result.conflicts.length} contradiction(s) detected across documents:
                          </p>
                          {result.conflicts.slice(0, 10).map((c, i) => (
                            <ConflictCard key={i} conflict={c} />
                          ))}
                          {result.conflicts.length > 10 && (
                            <p className="text-xs text-sentinel-gray text-center pt-1">
                              … and {result.conflicts.length - 10} more. View the Conflicts page for the full list.
                            </p>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <EmptyState
              icon={Search}
              title="Ready to Investigate"
              description="Ask a natural-language question about your documents. DocuSentinel retrieves real evidence, detects conflicts, and never invents facts."
            />
          )}
        </div>
      </div>
    </div>
  )
}

function ConflictCard({ conflict }: { conflict: any }) {
  return (
    <div className="rounded-lg border border-amber-500/25 overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2 bg-amber-500/10">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
        <span className="text-xs font-bold text-amber-300 uppercase tracking-wide">
          {conflict.field.replace(/_/g, ' ')}
        </span>
        <SeverityBadge severity={conflict.severity} />
      </div>
      <div className="grid grid-cols-2 divide-x divide-amber-500/20">
        <div className="p-3">
          <p className="text-[10px] text-sentinel-gray mb-1 uppercase tracking-wide truncate">
            {conflict.source_a} · p.{conflict.page_a}
          </p>
          <p className="text-sm font-semibold text-sentinel-text font-mono break-words">{conflict.value_a}</p>
        </div>
        <div className="p-3">
          <p className="text-[10px] text-sentinel-gray mb-1 uppercase tracking-wide truncate">
            {conflict.source_b} · p.{conflict.page_b}
          </p>
          <p className="text-sm font-semibold text-sentinel-text font-mono break-words">{conflict.value_b}</p>
        </div>
      </div>
    </div>
  )
}
