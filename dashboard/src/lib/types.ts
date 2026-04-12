export interface VaultSummary {
  vault_id: string;
  repo_path: string;
  total_chunks: number;
  stale_chunks: number;
  secret_chunks: number;
  total_files: number;
  generation: number;
  wing_rooms: Record<string, Record<string, number>>;
  wing?: string;
  last_commit?: string;
  last_branch?: string;
}

export interface SearchResult {
  content_hash: string;
  content: string;
  file_path: string;
  wing: string;
  room: string;
  importance: number;
  created_at: string;
  git_commit: string | null;
  git_branch: string | null;
  score: number;
  sources: string[];
  vault_id?: string;
  repo_path?: string;
}

export interface Chunk {
  content_hash: string;
  content: string;
  file_path: string;
  file_hash: string;
  wing: string;
  room: string;
  generation: number;
  created_at: string;
  updated_at: string;
  last_accessed: string | null;
  access_count: number;
  importance: number;
  git_commit: string | null;
  git_branch: string | null;
  is_stale: number;
  is_secret: number;
  added_by: string;
}

export interface VaultFile {
  file_path: string;
  file_hash: string;
  last_mined_at: string;
  last_commit: string | null;
  chunk_count: number;
  is_deleted: number;
}

export interface KGFact {
  direction: string;
  subject: string;
  predicate: string;
  object: string;
  valid_from: string | null;
  valid_to: string | null;
  confidence: number;
  current: boolean;
}

export interface KGEntity {
  id: string;
  name: string;
  type: string;
  properties: string;
  created_at: string;
}

export interface KGStats {
  entities: number;
  triples: number;
  current_facts: number;
  expired_facts: number;
  relationship_types: string[];
}

export interface MineStats {
  files_scanned: number;
  files_processed: number;
  files_skipped: number;
  files_deleted: number;
  chunks_added: number;
  chunks_updated: number;
  chunks_stale: number;
  secrets_found: number;
}

export interface GCLogEntry {
  id: number;
  action: string;
  content_hash: string | null;
  file_path: string | null;
  reason: string;
  performed_at: string;
}

export interface BudgetReport {
  tokens: number;
  budget: number;
  loaded?: number;
  deduped?: number;
}

export interface WakeUpResult {
  context: string;
  total_tokens: number;
  l0: BudgetReport;
  l1: BudgetReport;
}

export interface PaginatedChunks {
  chunks: Chunk[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}
