/**
 * DocuSentinel AI - Evidence Relation Graph
 * Visualizes documents, claims, and conflicts as an interactive node graph.
 * Uses React Flow for rendering.
 *
 * Node types:
 *   document — blue/cyan card
 *   claim    — green card (consistent) or amber (conflicting)
 *
 * Edge types:
 *   supports    — cyan dashed
 *   conflict    — red/amber animated
 */

import { useCallback, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import ReactFlow, {
  Node, Edge, Background, Controls, MiniMap,
  BackgroundVariant, useNodesState, useEdgesState,
  MarkerType, Handle, Position, NodeProps,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { api, GraphData } from '@/api/client'
import { PageLoader } from '@/components/LoadingSpinner'
import EmptyState from '@/components/EmptyState'
import { Network } from 'lucide-react'
import clsx from 'clsx'

// ── Custom Node: Document ─────────────────────────────────────────────────

function DocumentNode({ data }: NodeProps) {
  return (
    <div className={clsx(
      'px-4 py-3 rounded-xl border min-w-[160px] max-w-[200px]',
      'bg-[#0a1628] border-[#00d4ff]/40 shadow-[0_0_20px_rgba(0,212,255,0.15)]',
    )}>
      <Handle type="source" position={Position.Bottom} className="!bg-[#00d4ff] !border-[#00d4ff]" />
      <div className="flex items-center gap-2 mb-1">
        <div className="w-6 h-6 rounded bg-[#00d4ff]/10 border border-[#00d4ff]/30 flex items-center justify-center flex-shrink-0">
          <span className="text-[8px] font-bold text-[#00d4ff]">{data.file_type || 'DOC'}</span>
        </div>
        <span className="text-[10px] font-semibold text-[#00d4ff] uppercase tracking-wide">Document</span>
      </div>
      <p className="text-[11px] text-[#e2e8f0] leading-tight truncate" title={data.label}>
        {data.label}
      </p>
      {data.is_demo && (
        <span className="mt-1 inline-block text-[8px] px-1.5 py-0.5 rounded bg-[#00d4ff]/10 text-[#00d4ff]">DEMO</span>
      )}
    </div>
  )
}

// ── Custom Node: Claim ────────────────────────────────────────────────────

function ClaimNode({ data }: NodeProps) {
  const isConflicted = data.is_conflicted
  return (
    <div className={clsx(
      'px-3 py-2.5 rounded-lg border min-w-[140px] max-w-[190px]',
      isConflicted
        ? 'bg-amber-900/20 border-amber-500/40 shadow-[0_0_16px_rgba(245,158,11,0.15)]'
        : 'bg-emerald-900/20 border-emerald-500/30 shadow-[0_0_16px_rgba(16,185,129,0.1)]',
    )}>
      <Handle type="target" position={Position.Top} className={clsx(
        '!border-2',
        isConflicted ? '!bg-amber-500 !border-amber-500' : '!bg-emerald-500 !border-emerald-500'
      )} />
      <Handle type="source" position={Position.Bottom} className={clsx(
        '!border-2',
        isConflicted ? '!bg-amber-500 !border-amber-500' : '!bg-emerald-500 !border-emerald-500'
      )} />
      <div className="flex items-center gap-1.5 mb-1">
        <span className={clsx(
          'text-[8px] font-bold uppercase tracking-wider',
          isConflicted ? 'text-amber-400' : 'text-emerald-400'
        )}>
          {isConflicted ? '⚠ CONFLICT' : '✓ CLAIM'}
        </span>
      </div>
      <p className="text-[10px] font-medium text-[#e2e8f0] uppercase tracking-wide mb-0.5">
        {data.field?.replace(/_/g, ' ') || 'Claim'}
      </p>
      <p className="text-[11px] text-[#94a3b8] leading-tight truncate" title={data.raw_value}>
        {data.raw_value}
      </p>
    </div>
  )
}

const NODE_TYPES = { document: DocumentNode, claim: ClaimNode }

// ── Layout helper: simple tree layout ────────────────────────────────────

function applyLayout(rawNodes: Node[], rawEdges: Edge[]): Node[] {
  const DOC_Y   = 80
  const CLAIM_Y = 280
  const DOC_GAP   = 240
  const CLAIM_GAP = 200

  const docNodes   = rawNodes.filter(n => n.type === 'document')
  const claimNodes = rawNodes.filter(n => n.type === 'claim')

  // Center documents
  const docStartX = -(docNodes.length - 1) * DOC_GAP / 2
  docNodes.forEach((n, i) => {
    n.position = { x: docStartX + i * DOC_GAP, y: DOC_Y }
  })

  // Center claims below
  const claimStartX = -(claimNodes.length - 1) * CLAIM_GAP / 2
  claimNodes.forEach((n, i) => {
    n.position = { x: claimStartX + i * CLAIM_GAP, y: CLAIM_Y }
  })

  return [...docNodes, ...claimNodes]
}

// ── Main Component ────────────────────────────────────────────────────────

export default function EvidenceGraph() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  const { data: graphData, isLoading, isError } = useQuery({
    queryKey: ['graph'],
    queryFn: () => api.getGraphData(),
    refetchInterval: 30_000,
  })

  useEffect(() => {
    if (!graphData) return
    buildGraph(graphData)
  }, [graphData])

  const buildGraph = useCallback((data: GraphData) => {
    // Identify conflicted claim node IDs
    const conflictedNodeIds = new Set<string>()
    data.edges
      .filter(e => e.type === 'conflict')
      .forEach(e => {
        conflictedNodeIds.add(e.source)
        conflictedNodeIds.add(e.target)
      })

    // Build React Flow nodes
    const rfNodes: Node[] = data.nodes.map(n => ({
      id:   n.id,
      type: n.type === 'document' ? 'document' : 'claim',
      position: { x: 0, y: 0 },  // will be set by layout
      data: {
        ...n.data,
        label:         n.label,
        field:         n.data?.field,
        raw_value:     n.data?.raw_value,
        is_conflicted: conflictedNodeIds.has(n.id),
      },
    }))

    // Build React Flow edges
    const rfEdges: Edge[] = data.edges.map(e => {
      const isConflict = e.type === 'conflict'
      const sev = e.severity

      return {
        id:           e.id,
        source:       e.source,
        target:       e.target,
        label:        e.label,
        type:         isConflict ? 'straight' : 'smoothstep',
        animated:     isConflict,
        style: {
          stroke: isConflict
            ? (sev === 'HIGH' ? '#ef4444' : '#f59e0b')
            : 'rgba(0,212,255,0.35)',
          strokeWidth: isConflict ? 2.5 : 1.5,
          strokeDasharray: isConflict ? '0' : '5 3',
        },
        markerEnd: isConflict ? {
          type: MarkerType.ArrowClosed,
          color: sev === 'HIGH' ? '#ef4444' : '#f59e0b',
        } : undefined,
        labelStyle: {
          fill: isConflict ? '#f59e0b' : '#64748b',
          fontSize: 9,
          fontWeight: isConflict ? 700 : 400,
        },
        labelBgStyle: {
          fill: '#0a1628',
          fillOpacity: 0.8,
        },
      }
    })

    const laid = applyLayout(rfNodes, rfEdges)
    setNodes(laid)
    setEdges(rfEdges)
  }, [setNodes, setEdges])

  if (isLoading) return <PageLoader label="Building evidence graph..." />

  if (isError || !graphData) return (
    <div className="flex items-center justify-center h-full">
      <EmptyState
        icon={Network}
        title="Graph unavailable"
        description="Upload and index documents to see the evidence relation graph."
      />
    </div>
  )

  if (graphData.nodes.length === 0) return (
    <div className="flex items-center justify-center h-full">
      <EmptyState
        icon={Network}
        title="No graph data yet"
        description="Upload documents to populate the evidence relation graph."
      />
    </div>
  )

  return (
    <div className="w-full h-full relative">
      {/* Legend */}
      <div className="absolute top-3 right-3 z-10 glass-card p-3 text-xs space-y-1.5">
        <p className="text-[10px] uppercase tracking-widest text-sentinel-gray mb-2">Legend</p>
        <LegendItem color="border-[#00d4ff]/40 bg-[#00d4ff]/5"  label="Document" />
        <LegendItem color="border-emerald-500/30 bg-emerald-900/10" label="Consistent Claim" />
        <LegendItem color="border-amber-500/40 bg-amber-900/10"  label="Conflicting Claim" />
        <div className="pt-1 border-t border-sentinel-border space-y-1">
          <EdgeLegend color="#00d4ff" dash label="mentions" />
          <EdgeLegend color="#f59e0b" solid label="contradicts" />
        </div>
      </div>

      {/* Summary */}
      <div className="absolute top-3 left-3 z-10 glass-card px-3 py-2 text-xs flex items-center gap-4">
        <span className="text-sentinel-gray">{graphData.summary.documents} docs</span>
        <span className="text-sentinel-gray">{graphData.summary.claims} claims</span>
        <span className={graphData.summary.conflicts > 0 ? 'text-amber-400 font-semibold' : 'text-sentinel-gray'}>
          {graphData.summary.conflicts} conflicts
        </span>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={NODE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        maxZoom={2}
        defaultEdgeOptions={{ type: 'smoothstep' }}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={24}
          size={1}
          color="rgba(0,212,255,0.06)"
        />
        <Controls
          className="!bg-sentinel-surface !border-sentinel-border"
          showInteractive={false}
        />
        <MiniMap
          nodeColor={n =>
            n.type === 'document' ? '#00d4ff'
            : (n.data?.is_conflicted ? '#f59e0b' : '#10b981')
          }
          maskColor="rgba(5,12,26,0.7)"
          style={{ background: '#0a1628', border: '1px solid #1a2d4a' }}
        />
      </ReactFlow>
    </div>
  )
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className={`w-4 h-3 rounded border ${color}`} />
      <span className="text-[10px] text-sentinel-gray">{label}</span>
    </div>
  )
}

function EdgeLegend({ color, dash, solid, label }: {
  color: string; dash?: boolean; solid?: boolean; label: string
}) {
  return (
    <div className="flex items-center gap-2">
      <svg width="20" height="8">
        <line
          x1="0" y1="4" x2="20" y2="4"
          stroke={color}
          strokeWidth="2"
          strokeDasharray={dash ? '4 2' : '0'}
        />
      </svg>
      <span className="text-[10px] text-sentinel-gray">{label}</span>
    </div>
  )
}
