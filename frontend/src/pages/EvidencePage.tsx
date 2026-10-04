import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { Database, ChevronLeft, ChevronRight, FileText } from 'lucide-react'
import { DocumentStatusBadge } from '@/components/StatusBadge'
import { PageLoader } from '@/components/LoadingSpinner'
import EmptyState from '@/components/EmptyState'
import EvidenceGraph from '@/components/EvidenceGraph'
import clsx from 'clsx'

export default function EvidencePage() {
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [activeView, setActiveView] = useState<'browser' | 'graph'>('graph')

  const { data: docsData } = useQuery({
    queryKey: ['documents'],
    queryFn: () => api.getDocuments(),
  })

  const { data: chunksData, isLoading: chunksLoading } = useQuery({
    queryKey: ['chunks', selectedDocId, page],
    queryFn: () => api.getDocumentChunks(selectedDocId!, page, 15),
    enabled: !!selectedDocId && activeView === 'browser',
  })

  const readyDocs = (docsData?.documents ?? []).filter(d => d.status === 'ready')
  const totalPages = Math.ceil((chunksData?.total_chunks ?? 0) / 15)

  return (
    <div className="space-y-6 animate-slide-up">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-sentinel-text">Evidence Panel</h2>
          <p className="text-sm text-sentinel-gray mt-0.5">
            Browse indexed evidence and visualize document relationships
          </p>
        </div>
        <div className="flex rounded-lg overflow-hidden border border-sentinel-border">
          {(['graph', 'browser'] as const).map(v => (
            <button
              key={v}
              onClick={() => setActiveView(v)}
              className={clsx(
                'px-4 py-2 text-xs font-medium transition-colors capitalize',
                activeView === v
                  ? 'bg-sentinel-cyan/10 text-sentinel-cyan'
                  : 'text-sentinel-gray hover:text-sentinel-text'
              )}
            >
              {v === 'graph' ? 'Relation Graph' : 'Evidence Browser'}
            </button>
          ))}
        </div>
      </div>

      {activeView === 'graph' && (
        <div className="glass-card overflow-hidden" style={{ height: '600px' }}>
          <EvidenceGraph />
        </div>
      )}

      {activeView === 'browser' && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* Document list */}
          <div className="glass-card p-4 lg:col-span-1">
            <p className="section-header">Documents</p>
            {readyDocs.length === 0 ? (
              <p className="text-xs text-sentinel-gray">No indexed documents yet.</p>
            ) : (
              <div className="space-y-1.5">
                {readyDocs.map(doc => (
                  <button
                    key={doc.id}
                    onClick={() => { setSelectedDocId(doc.id); setPage(1) }}
                    className={clsx(
                      'w-full text-left p-2.5 rounded-lg transition-all text-sm',
                      selectedDocId === doc.id
                        ? 'bg-sentinel-cyan/10 border border-sentinel-cyan/20 text-sentinel-cyan'
                        : 'text-sentinel-gray hover:text-sentinel-text hover:bg-sentinel-border/50'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5 flex-shrink-0" />
                      <span className="text-xs truncate">{doc.original_name}</span>
                    </div>
                    <p className="text-[10px] mt-0.5 ml-5 text-sentinel-gray">
                      {doc.page_count}p · {doc.chunk_count} chunks
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Chunks */}
          <div className="lg:col-span-3 space-y-3">
            {!selectedDocId ? (
              <EmptyState
                icon={Database}
                title="Select a document"
                description="Choose a document on the left to browse its evidence chunks."
              />
            ) : chunksLoading ? (
              <PageLoader label="Loading chunks..." />
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <p className="text-xs text-sentinel-gray">
                    {chunksData?.document_name} ·{' '}
                    <span className="text-sentinel-text">{chunksData?.total_chunks} chunks</span>
                  </p>
                  {totalPages > 1 && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1}
                        className="p-1 rounded text-sentinel-gray hover:text-sentinel-text disabled:opacity-30 transition-colors"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <span className="text-xs text-sentinel-gray">{page} / {totalPages}</span>
                      <button
                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                        className="p-1 rounded text-sentinel-gray hover:text-sentinel-text disabled:opacity-30 transition-colors"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                </div>
                <div className="space-y-2">
                  {(chunksData?.chunks ?? []).map((chunk: any) => (
                    <div key={chunk.chunk_id} className="glass-card p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-[10px] font-mono text-sentinel-cyan">#{chunk.chunk_index}</span>
                        <span className="text-[10px] text-sentinel-gray">Page {chunk.page_number}</span>
                        {chunk.section && (
                          <span className="text-[10px] text-sentinel-gray">· {chunk.section}</span>
                        )}
                      </div>
                      <p className="text-xs text-sentinel-text-dim leading-relaxed">{chunk.text}</p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
