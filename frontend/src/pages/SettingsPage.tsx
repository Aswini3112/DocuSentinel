import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { Server, Database, Cpu, Key, Info, CheckCircle, AlertCircle, XCircle, ExternalLink } from 'lucide-react'
import clsx from 'clsx'

export default function SettingsPage() {
  const { data: health, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.getHealth(),
    refetchInterval: 10_000,
  })

  const llmConfigured = health?.llm_status === 'CONFIGURED'
  const llmError      = health?.llm_status === 'ERROR'

  return (
    <div className="space-y-6 animate-slide-up max-w-2xl">
      <div>
        <h2 className="text-xl font-bold text-sentinel-text">Settings</h2>
        <p className="text-sm text-sentinel-gray mt-0.5">System configuration and live status</p>
      </div>

      {/* System Status */}
      <div className="glass-card p-5 space-y-1">
        <p className="section-header">System Status</p>
        <StatusRow
          icon={Server}
          label="API Server"
          value={health?.status === 'ok' ? 'Online' : (isLoading ? 'Checking…' : 'Offline')}
          ok={health?.status === 'ok'}
        />
        <StatusRow
          icon={Database}
          label="Database"
          value={health?.database || (isLoading ? 'Checking…' : '—')}
          ok={health?.database === 'ok'}
        />
        <StatusRow
          icon={Database}
          label="Vector Store"
          value={health?.vector_store || (isLoading ? 'Checking…' : '—')}
          ok={(health?.vector_store ?? '').startsWith('ok')}
        />
        {/* AI provider row — the most important, always honest */}
        <div className="flex items-center gap-3 py-3 border-b border-sentinel-border last:border-0">
          <Cpu className="w-4 h-4 text-sentinel-gray flex-shrink-0" />
          <span className="text-sm text-sentinel-text-dim w-32">AI Provider</span>
          <div className="flex-1">
            <span className={clsx('text-sm font-semibold',
              llmConfigured ? 'text-sentinel-green' :
              llmError      ? 'text-red-400'        : 'text-sentinel-amber'
            )}>
              {llmConfigured
                ? `ONLINE — ${health?.llm_model}`
                : llmError
                ? `ERROR — ${health?.llm_message}`
                : 'NOT CONFIGURED'}
            </span>
            {!llmConfigured && (
              <p className="text-xs text-sentinel-gray mt-0.5">
                {llmError
                  ? 'Check your LLM_API_KEY in backend/.env'
                  : 'Add LLM_API_KEY to backend/.env to enable AI-powered answers'}
              </p>
            )}
          </div>
          <div className={clsx('w-2 h-2 rounded-full flex-shrink-0',
            llmConfigured ? 'bg-sentinel-green animate-pulse' :
            llmError      ? 'bg-red-400'                      : 'bg-sentinel-amber'
          )} />
        </div>
        <StatusRow
          icon={Info}
          label="Version"
          value={health?.version || '1.0.0'}
          ok={true}
        />
      </div>

      {/* AI Setup Guide */}
      {!llmConfigured && (
        <div className={clsx(
          'glass-card p-5 border',
          llmError ? 'border-red-500/30' : 'border-sentinel-amber/30'
        )}>
          <div className="flex items-start gap-3">
            <AlertCircle className={clsx('w-5 h-5 flex-shrink-0 mt-0.5',
              llmError ? 'text-red-400' : 'text-sentinel-amber'
            )} />
            <div className="space-y-3 flex-1">
              <p className={clsx('text-sm font-semibold',
                llmError ? 'text-red-300' : 'text-sentinel-amber'
              )}>
                {llmError ? 'AI Provider Error' : 'AI Provider Not Configured'}
              </p>
              <p className="text-xs text-sentinel-text-dim leading-relaxed">
                DocuSentinel works without an AI key — answers are built directly from retrieved
                evidence. Add a key to get natural-language AI reasoning on top of the evidence.
              </p>
              <div className="space-y-2">
                <p className="text-xs font-semibold text-sentinel-text">Quick setup (free):</p>
                <ol className="text-xs text-sentinel-text-dim space-y-1 list-decimal list-inside">
                  <li>
                    Get a free API key at{' '}
                    <a
                      href="https://console.groq.com"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sentinel-cyan hover:underline inline-flex items-center gap-1"
                    >
                      console.groq.com <ExternalLink className="w-3 h-3" />
                    </a>
                  </li>
                  <li>Open <code className="font-mono bg-sentinel-border px-1 rounded">backend/.env</code></li>
                  <li>Set <code className="font-mono bg-sentinel-border px-1 rounded">LLM_API_KEY=gsk_...</code></li>
                  <li>The backend auto-reloads — no restart needed</li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Environment Variables Reference */}
      <div className="glass-card p-5 space-y-3">
        <p className="section-header">Environment Variables</p>
        <p className="text-xs text-sentinel-text-dim">
          Edit <code className="font-mono text-sentinel-cyan bg-sentinel-border px-1.5 py-0.5 rounded">backend/.env</code>{' '}
          to configure the system. Copy from{' '}
          <code className="font-mono text-sentinel-cyan bg-sentinel-border px-1.5 py-0.5 rounded">backend/.env.example</code>{' '}
          as a starting point.
        </p>
        <div className="space-y-1.5">
          {[
            { key: 'LLM_API_KEY',         desc: 'Your API key (Groq, OpenAI, etc.)',            required: true },
            { key: 'LLM_MODEL',            desc: 'Model name — e.g. llama-3.3-70b-versatile',   required: false },
            { key: 'LLM_BASE_URL',         desc: 'API base URL — blank = OpenAI default',        required: false },
            { key: 'CHUNK_SIZE',           desc: 'Words per chunk (default: 150)',               required: false },
            { key: 'TOP_K_RETRIEVAL',      desc: 'Evidence chunks to retrieve (default: 8)',     required: false },
            { key: 'SIMILARITY_THRESHOLD', desc: 'Min similarity score 0–1 (default: 0.05)',     required: false },
            { key: 'MAX_FILE_SIZE_MB',     desc: 'Max upload size in MB (default: 50)',           required: false },
          ].map(item => (
            <div key={item.key} className="flex items-center gap-3 p-2.5 rounded-lg bg-sentinel-bg/50 border border-sentinel-border">
              <Key className="w-3.5 h-3.5 text-sentinel-gray flex-shrink-0" />
              <code className="text-xs font-mono text-sentinel-cyan w-52 flex-shrink-0">{item.key}</code>
              <span className="text-xs text-sentinel-gray flex-1">{item.desc}</span>
              {item.required && (
                <span className="text-[10px] font-bold text-sentinel-amber px-1.5 py-0.5 rounded bg-sentinel-amber/10 border border-sentinel-amber/20">
                  REQUIRED
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* About */}
      <div className="glass-card p-5 space-y-3">
        <p className="section-header">About DocuSentinel AI</p>
        <div className="space-y-2 text-sm text-sentinel-text-dim">
          <p>Built for <strong className="text-sentinel-text">ALGOTHON'26</strong> — Problem Statement ALG-AI-02: Intelligent Document Investigator.</p>
          <p className="italic text-sentinel-cyan">"Investigate documents. Trace evidence. Detect conflicts. Trust the answer."</p>
          <p>
            DocuSentinel focuses on <strong className="text-sentinel-text">whether an answer can be trusted</strong>,
            not just whether an answer can be generated. Every response is grounded in retrieved evidence,
            conflicts are explicitly detected and surfaced, and uncertainty is communicated — never hidden.
          </p>
          <div className="grid grid-cols-2 gap-2 pt-2">
            {[
              ['Evidence Retrieval', 'TF-IDF vector search'],
              ['Conflict Detection', 'Dual-engine (DB + inline)'],
              ['LLM', 'Any OpenAI-compatible API'],
              ['Storage', 'SQLite + NumPy vector store'],
            ].map(([label, value]) => (
              <div key={label} className="p-2 rounded-lg bg-sentinel-bg/50 border border-sentinel-border">
                <p className="text-[10px] text-sentinel-gray uppercase tracking-wide">{label}</p>
                <p className="text-xs text-sentinel-text mt-0.5">{value}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function StatusRow({ icon: Icon, label, value, ok }: {
  icon: any; label: string; value: string; ok: boolean
}) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-sentinel-border last:border-0">
      <Icon className="w-4 h-4 text-sentinel-gray flex-shrink-0" />
      <span className="text-sm text-sentinel-text-dim w-32">{label}</span>
      <span className={clsx('text-sm font-medium flex-1', ok ? 'text-sentinel-green' : 'text-sentinel-amber')}>
        {value}
      </span>
      <div className={clsx('w-2 h-2 rounded-full flex-shrink-0', ok ? 'bg-sentinel-green' : 'bg-sentinel-amber')} />
    </div>
  )
}
