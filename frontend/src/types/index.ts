/**
 * TypeScript types for AI-SupraAgent frontend
 */

// ═══════════════════════════════════════════════════════════════
// Chat Types
// ═══════════════════════════════════════════════════════════════

export interface ChatSession {
  id: string;
  title: string | null;
  user_id: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tool_calls: ToolCallData | null;
  created_at: string;
}

export interface ToolCallData {
  calls: ToolCall[];
}

export interface ToolCall {
  tool_name: string;
  tool_input: Record<string, unknown>;
  status: 'pending' | 'running' | 'completed' | 'error';
  result?: unknown;
}

export interface ChatStreamRequest {
  message: string;
  session_id?: string;
  use_rag?: boolean;
  use_analytics?: boolean;
}

export interface StreamEvent {
  event: 'text' | 'tool_call' | 'error' | 'done';
  data: string | ToolCall | { session_id: string } | { error: string };
}

// ═══════════════════════════════════════════════════════════════
// Document Types
// ═══════════════════════════════════════════════════════════════

export type DocumentStatus = 'pending' | 'processing' | 'indexed' | 'error';

export interface Document {
  id: string;
  filename: string;
  original_name: string;
  mime_type: string;
  file_size: number;
  status: DocumentStatus;
  chunk_count: number;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  page: number;
  page_size: number;
}

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  original_name: string;
  mime_type: string;
  file_size: number;
  status: DocumentStatus;
  message: string;
}

export interface SearchResult {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  token_count: number | null;
  similarity: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
}

// ═══════════════════════════════════════════════════════════════
// API Types
// ═══════════════════════════════════════════════════════════════

export interface ApiError {
  detail: string;
  status_code?: number;
}

export interface HealthResponse {
  status: 'healthy' | 'unhealthy';
  service: string;
  version?: string;
}

// ═══════════════════════════════════════════════════════════════
// UI State Types
// ═══════════════════════════════════════════════════════════════

export interface AppState {
  sidebarOpen: boolean;
  currentView: 'chat' | 'knowledge';
  currentSessionId: string | null;
}

export type ViewType = 'chat' | 'knowledge';
