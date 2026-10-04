/**
 * DocuSentinel AI - API Client
 * Typed wrapper around all backend endpoints.
 */

import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || '/api'

const http = axios.create({ baseURL: BASE, timeout: 120_000 })

// ── Types ──────────────────────────────────────────────────────────────────

export interface Document {
  id: string
  original_name: string
  file_type: string
  file_size: number
  status: 'uploading' | 'extracting' | 'indexing' | 'ready' | 'failed'
  page_count: number
  chunk_count: number
  is_demo: boolean
  error_message?: string
  created_at: string
  updated_at: string
}

export interface EvidenceItem {
  chunk_id: string
  document_id: string
  document_name: string
  page_number: number
  section?: string
  text: string
  relevance_score: number
}

export interface SourceReference {
  document_id: string
  document_name: string
  page_number: number
  section?: string
  excerpt: string
}

export interface InlineConflict {
  field: string
  value_a: string
  source_a: string
  page_a: number
  value_b: string
  source_b: string
  page_b: number
  severity: 'HIGH' | 'MEDIUM' | 'LOW'
}

export interface InvestigateResponse {
  id: string
  question: string
  answer: string
  answer_status: 'VERIFIED' | 'CONFLICTING' | 'UNCERTAIN' | 'NOT_FOUND'
  confidence_score: number
  confidence_percent: number
  confidence_reason: string
  evidence_strength: 'High' | 'Medium' | 'Low' | 'None'
  has_conflict: boolean
  evidence: EvidenceItem[]
  sources: SourceReference[]
  conflicts: InlineConflict[]
  // LLM provider transparency
  llm_used: boolean
  llm_status: 'CONFIGURED' | 'NOT_CONFIGURED' | 'ERROR'
  llm_status_msg: string
  created_at: string
}

export interface InvestigationListItem {
  id: string
  question: string
  answer_status: string
  confidence_score: number
  has_conflict: boolean
  created_at: string
}

export interface Conflict {
  id: string
  field: string
  document_a_name: string
  document_b_name: string
  document_a_id: string
  document_b_id: string
  value_a: string
  value_b: string
  severity: 'HIGH' | 'MEDIUM' | 'LOW'
  status: 'open' | 'resolved' | 'ignored'
  description?: string
  created_at: string
}

export interface DashboardStats {
  documents_analyzed: number
  claims_extracted: number
  conflicts_detected: number
  uncertain_claims: number
  evidence_coverage: number
  answer_confidence: number
  conflict_risk: number
}

export interface HealthResponse {
  status: string
  app: string
  version: string
  database: string
  vector_store: string
  llm: string
  // New honest LLM status fields
  llm_status: 'CONFIGURED' | 'NOT_CONFIGURED' | 'ERROR'
  llm_model: string | null
  llm_message: string
}

export interface LLMStatus {
  status: 'CONFIGURED' | 'NOT_CONFIGURED' | 'ERROR'
  message: string
  model: string | null
}

export interface GraphData {
  nodes: Array<{ id: string; type: string; label: string; data: Record<string, any> }>
  edges: Array<{ id: string; source: string; target: string; label: string; type: string; severity?: string }>
  summary: { documents: number; claims: number; conflicts: number }
}

// ── API Methods ─────────────────────────────────────────────────────────────

export const api = {
  // Health
  getHealth:    () => http.get<HealthResponse>('/health').then(r => r.data),
  getStats:     () => http.get<DashboardStats>('/stats').then(r => r.data),
  getLLMStatus: () => http.get<LLMStatus>('/llm-status').then(r => r.data),

  // Documents
  uploadDocument: (file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    return http.post<Document>('/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: e => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
      },
    }).then(r => r.data)
  },
  getDocuments: () =>
    http.get<{ documents: Document[]; total: number }>('/documents').then(r => r.data),
  getDocument: (id: string) =>
    http.get<Document & { sample_chunks: any[] }>(`/documents/${id}`).then(r => r.data),
  deleteDocument: (id: string) => http.delete(`/documents/${id}`),
  loadDemoDocuments: () =>
    http.post<{ message: string; files: string[] }>('/documents/demo/load').then(r => r.data),

  // Investigate
  investigate: (question: string, document_ids?: string[]) =>
    http.post<InvestigateResponse>('/investigate', { question, document_ids }).then(r => r.data),
  getInvestigations: (limit = 20) =>
    http.get<{ investigations: InvestigationListItem[]; total: number }>('/investigations', {
      params: { limit },
    }).then(r => r.data),
  getInvestigation: (id: string) =>
    http.get<InvestigateResponse>(`/investigations/${id}`).then(r => r.data),

  // Conflicts
  getConflicts: (severity?: string, status?: string) =>
    http.get<{ conflicts: Conflict[]; total: number; high: number; medium: number; low: number }>(
      '/conflicts', { params: { severity, status } }
    ).then(r => r.data),
  updateConflict: (id: string, status: string, note?: string) =>
    http.patch<Conflict>(`/conflicts/${id}`, { status, resolution_note: note }).then(r => r.data),

  // Evidence
  getEvidenceChunk:   (chunkId: string) =>
    http.get(`/evidence/${chunkId}`).then(r => r.data),
  getDocumentChunks:  (docId: string, page = 1, pageSize = 20) =>
    http.get(`/evidence/document/${docId}`, { params: { page, page_size: pageSize } }).then(r => r.data),
  getGraphData: () =>
    http.get<GraphData>('/evidence/graph/data').then(r => r.data),
}
