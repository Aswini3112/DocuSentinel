import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import toast from 'react-hot-toast'
import { api, Document } from '@/api/client'
import {
  Upload, FileText, Trash2, RefreshCw, Play,
  CheckCircle, AlertCircle, ChevronDown, ChevronUp,
  FolderOpen, Sparkles
} from 'lucide-react'
import { DocumentStatusBadge } from '@/components/StatusBadge'
import { PageLoader } from '@/components/LoadingSpinner'
import EmptyState from '@/components/EmptyState'
import clsx from 'clsx'
import { formatDistanceToNow } from 'date-fns'

function formatBytes(b: number) {
  if (b < 1024) return `${b} B`
  if (b < 1024 ** 2) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1024 ** 2).toFixed(1)} MB`
}

export default function DocumentsPage() {
  const qc = useQueryClient()
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [uploading, setUploading] = useState<{ name: string; progress: number }[]>([])

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['documents'],
    queryFn: () => api.getDocuments(),
    refetchInterval: 3_000,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteDocument(id),
    onSuccess: () => {
      toast.success('Document deleted.')
      qc.invalidateQueries({ queryKey: ['documents'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
    },
    onError: () => toast.error('Failed to delete document.'),
  })

  const demoMutation = useMutation({
    mutationFn: () => api.loadDemoDocuments(),
    onSuccess: (data) => {
      toast.success(`${data.files.length} demo documents queued for ingestion.`)
      qc.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: () => toast.error('Failed to load demo documents.'),
  })

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    for (const file of acceptedFiles) {
      setUploading(prev => [...prev, { name: file.name, progress: 0 }])
      try {
        await api.uploadDocument(file, (pct) => {
          setUploading(prev => prev.map(u => u.name === file.name ? { ...u, progress: pct } : u))
        })
        toast.success(`${file.name} uploaded — processing...`)
        qc.invalidateQueries({ queryKey: ['documents'] })
      } catch (err: any) {
        const msg = err.response?.data?.detail || 'Upload failed.'
        toast.error(`${file.name}: ${msg}`)
      } finally {
        setUploading(prev => prev.filter(u => u.name !== file.name))
      }
    }
  }, [qc])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
    },
    multiple: true,
  })

  const documents = data?.documents ?? []
  const readyDocs = documents.filter(d => d.status === 'ready')

  return (
    <div className="space-y-6 animate-slide-up">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-sentinel-text">Document Library</h2>
          <p className="text-sm text-sentinel-gray mt-0.5">
            {documents.length} documents · {readyDocs.length} indexed
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => demoMutation.mutate()}
            disabled={demoMutation.isPending}
            className="btn-secondary text-xs"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {demoMutation.isPending ? 'Loading…' : 'Load Demo Data'}
          </button>
          <button onClick={() => refetch()} className="btn-secondary text-xs">
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
        </div>
      </div>

      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={clsx(
          'border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all duration-200',
          isDragActive
            ? 'border-sentinel-cyan bg-sentinel-cyan/5 shadow-cyan-glow'
            : 'border-sentinel-border hover:border-sentinel-border-bright hover:bg-sentinel-surface'
        )}
      >
        <input {...getInputProps()} />
        <Upload className={clsx('w-8 h-8 mx-auto mb-3', isDragActive ? 'text-sentinel-cyan' : 'text-sentinel-gray')} />
        <p className="text-sm font-medium text-sentinel-text">
          {isDragActive ? 'Drop files here' : 'Drag & drop documents here'}
        </p>
        <p className="text-xs text-sentinel-gray mt-1">
          PDF, DOCX, TXT, PNG, JPG — up to 50 MB each
        </p>
        <button className="mt-4 btn-primary text-xs">
          <FolderOpen className="w-3.5 h-3.5" />
          Browse Files
        </button>
      </div>

      {/* Upload progress */}
      {uploading.length > 0 && (
        <div className="space-y-2">
          {uploading.map(u => (
            <div key={u.name} className="glass-card p-3 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center flex-shrink-0">
                <Upload className="w-4 h-4 text-blue-400 animate-bounce" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-sentinel-text truncate">{u.name}</p>
                <div className="mt-1 h-1 rounded-full bg-sentinel-border overflow-hidden">
                  <div
                    className="h-full bg-sentinel-cyan rounded-full transition-all duration-200"
                    style={{ width: `${u.progress}%` }}
                  />
                </div>
              </div>
              <span className="text-xs text-sentinel-gray font-mono">{u.progress}%</span>
            </div>
          ))}
        </div>
      )}

      {/* Document List */}
      {isLoading ? (
        <PageLoader label="Loading documents..." />
      ) : documents.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No documents yet"
          description="Upload documents above or load the demo dataset to get started."
        />
      ) : (
        <div className="space-y-2">
          {documents.map(doc => (
            <DocumentCard
              key={doc.id}
              doc={doc}
              expanded={expandedId === doc.id}
              onToggle={() => setExpandedId(expandedId === doc.id ? null : doc.id)}
              onDelete={() => deleteMutation.mutate(doc.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function DocumentCard({
  doc, expanded, onToggle, onDelete
}: {
  doc: Document
  expanded: boolean
  onToggle: () => void
  onDelete: () => void
}) {
  const { data: detail } = useQuery({
    queryKey: ['document', doc.id],
    queryFn: () => api.getDocument(doc.id),
    enabled: expanded && doc.status === 'ready',
  })

  return (
    <div className={clsx(
      'glass-card overflow-hidden transition-all duration-200',
      doc.status === 'failed' && 'border-red-500/20',
      doc.is_demo && 'border-sentinel-cyan/10',
    )}>
      <div className="p-4 flex items-center gap-4">
        {/* File type badge */}
        <div className="w-10 h-10 rounded-lg bg-sentinel-cyan/10 border border-sentinel-cyan/20 flex items-center justify-center flex-shrink-0">
          <span className="text-[10px] font-bold text-sentinel-cyan">{doc.file_type}</span>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-sentinel-text truncate">{doc.original_name}</p>
            {doc.is_demo && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-sentinel-cyan/10 text-sentinel-cyan border border-sentinel-cyan/20">
                DEMO
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-1">
            <DocumentStatusBadge status={doc.status} />
            {doc.status === 'ready' && (
              <>
                <span className="text-xs text-sentinel-gray">
                  {doc.page_count} pages
                </span>
                <span className="text-xs text-sentinel-gray">
                  {doc.chunk_count} chunks
                </span>
              </>
            )}
            <span className="text-xs text-sentinel-gray">{formatBytes(doc.file_size)}</span>
          </div>
          {doc.error_message && (
            <p className="text-xs text-red-400 mt-1 truncate">{doc.error_message}</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {doc.status === 'ready' && (
            <button
              onClick={onToggle}
              className="p-1.5 rounded-lg text-sentinel-gray hover:text-sentinel-text hover:bg-sentinel-border transition-colors"
            >
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          )}
          <button
            onClick={onDelete}
            className="p-1.5 rounded-lg text-sentinel-gray hover:text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Expanded: sample chunks */}
      {expanded && doc.status === 'ready' && (
        <div className="border-t border-sentinel-border p-4 space-y-3 bg-sentinel-bg/30">
          <p className="section-header">Sample Chunks</p>
          {detail?.sample_chunks?.map((chunk: any, i: number) => (
            <div key={i} className="evidence-highlight text-xs">
              <span className="text-sentinel-cyan font-mono mr-2">
                p.{chunk.page_number} {chunk.section ? `· ${chunk.section}` : ''}
              </span>
              {chunk.text}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
