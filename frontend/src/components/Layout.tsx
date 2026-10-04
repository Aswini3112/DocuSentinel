import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { useState } from 'react'
import {
  LayoutDashboard, FileText, Search, AlertTriangle,
  Database, Settings, Shield, ChevronLeft, ChevronRight,
  Activity, Cpu, AlertCircle, CheckCircle, XCircle
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import clsx from 'clsx'

const NAV_ITEMS = [
  { to: '/dashboard',   icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/documents',   icon: FileText,        label: 'Documents' },
  { to: '/investigate', icon: Search,          label: 'Investigate' },
  { to: '/conflicts',   icon: AlertTriangle,   label: 'Conflicts' },
  { to: '/evidence',    icon: Database,        label: 'Evidence' },
  { to: '/settings',    icon: Settings,        label: 'Settings' },
]

/** Translate backend llm_status into display config */
function llmStatusConfig(status?: string) {
  switch (status) {
    case 'CONFIGURED':
      return { color: 'text-sentinel-green', dot: 'bg-sentinel-green', label: 'AI Online', Icon: CheckCircle }
    case 'ERROR':
      return { color: 'text-red-400',        dot: 'bg-red-400',        label: 'AI Error',  Icon: XCircle }
    default:
      return { color: 'text-sentinel-amber', dot: 'bg-sentinel-amber', label: 'AI Not Configured', Icon: AlertCircle }
  }
}

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.getHealth(),
    refetchInterval: 30_000,
  })

  const systemOk = health?.status === 'ok'
  const llm = llmStatusConfig(health?.llm_status)

  const pageTitle = location.pathname.replace('/', '').replace('-', ' ') || 'Dashboard'

  return (
    <div className="flex h-screen bg-sentinel-bg overflow-hidden grid-bg">
      {/* ── Sidebar ──────────────────────────── */}
      <aside className={clsx(
        'flex flex-col bg-sentinel-surface border-r border-sentinel-border',
        'transition-all duration-300 ease-in-out flex-shrink-0',
        collapsed ? 'w-16' : 'w-60'
      )}>
        {/* Logo */}
        <div className={clsx(
          'flex items-center border-b border-sentinel-border',
          collapsed ? 'px-4 py-4 justify-center' : 'px-5 py-4 gap-3'
        )}>
          <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-sentinel-cyan/10 border border-sentinel-cyan/30 flex items-center justify-center">
            <Shield className="w-4 h-4 text-sentinel-cyan" />
          </div>
          {!collapsed && (
            <div>
              <div className="text-sm font-bold text-gradient-cyan leading-tight">DocuSentinel</div>
              <div className="text-[10px] text-sentinel-gray tracking-wider uppercase">AI</div>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx('nav-item', isActive && 'active', collapsed && 'justify-center px-2')
              }
              title={collapsed ? label : undefined}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* AI Provider status — always honest */}
        <div className={clsx('border-t border-sentinel-border p-3', collapsed && 'flex justify-center')}>
          {collapsed ? (
            <div className={clsx('w-2 h-2 rounded-full', llm.dot)} title={llm.label} />
          ) : (
            <div className="space-y-2">
              {/* System */}
              <div className="flex items-center gap-2">
                <Activity className="w-3 h-3 text-sentinel-gray flex-shrink-0" />
                <span className="text-[11px] text-sentinel-gray">System</span>
                <div className={clsx('ml-auto w-1.5 h-1.5 rounded-full',
                  systemOk ? 'bg-sentinel-green animate-pulse' : 'bg-sentinel-amber'
                )} />
                <span className={clsx('text-[11px] font-medium',
                  systemOk ? 'text-sentinel-green' : 'text-sentinel-amber'
                )}>
                  {systemOk ? 'Online' : 'Degraded'}
                </span>
              </div>
              {/* AI Provider */}
              <div className="flex items-center gap-2">
                <Cpu className="w-3 h-3 text-sentinel-gray flex-shrink-0" />
                <span className="text-[11px] text-sentinel-gray">AI</span>
                <div className={clsx('ml-auto w-1.5 h-1.5 rounded-full', llm.dot,
                  health?.llm_status === 'CONFIGURED' && 'animate-pulse'
                )} />
                <span className={clsx('text-[11px] font-medium', llm.color)}>
                  {health?.llm_status === 'CONFIGURED' ? 'Online' :
                   health?.llm_status === 'ERROR'      ? 'Error'  : 'Not Set'}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(c => !c)}
          className="border-t border-sentinel-border p-3 flex items-center justify-center
                     text-sentinel-gray hover:text-sentinel-text transition-colors"
        >
          {collapsed
            ? <ChevronRight className="w-4 h-4" />
            : <><ChevronLeft className="w-4 h-4" /><span className="text-xs ml-2">Collapse</span></>
          }
        </button>
      </aside>

      {/* ── Main Content ─────────────────────── */}
      <main className="flex-1 overflow-y-auto">
        {/* Top bar */}
        <header className="sticky top-0 z-10 bg-sentinel-bg/90 backdrop-blur border-b border-sentinel-border px-6 py-3">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-sm font-semibold text-sentinel-text capitalize">{pageTitle}</h1>
              <p className="text-xs text-sentinel-gray">
                Investigate documents. Trace evidence. Detect conflicts.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-xs text-sentinel-gray font-mono">
                {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
              </div>
              <div className="w-px h-4 bg-sentinel-border" />
              {/* AI status pill in header — always truthful */}
              <div className={clsx(
                'flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium',
                health?.llm_status === 'CONFIGURED'
                  ? 'bg-sentinel-green/10 border-sentinel-green/20 text-sentinel-green'
                  : health?.llm_status === 'ERROR'
                  ? 'bg-red-500/10 border-red-500/20 text-red-400'
                  : 'bg-sentinel-amber/10 border-sentinel-amber/20 text-sentinel-amber'
              )}>
                <llm.Icon className="w-3 h-3" />
                {health?.llm_status === 'CONFIGURED'
                  ? `AI: ${health.llm_model || 'Online'}`
                  : health?.llm_status === 'ERROR'
                  ? 'AI: Error'
                  : 'AI: Not Configured'}
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <div className="p-6 animate-fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
