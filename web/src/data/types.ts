export type ExecutionType = "tool" | "workflow" | "code" | "llm" | "hybrid";
export type RiskLevel = "low" | "medium" | "high" | "critical";
export type SourceType = "native" | "skill" | "openai_func" | "mcp_tool" | "custom";
export type ExecutionStatus = "pending" | "running" | "completed" | "failed";

export interface Cape {
  id: string;
  name: string;
  version: string;
  description: string;
  execution_type: ExecutionType;
  risk_level: RiskLevel;
  source: SourceType;
  tags: string[];
  intent_patterns: string[];
  model_adapters: string[];
  estimated_cost?: number;
  timeout_seconds?: number;
  created_at: string;
  updated_at: string;
}

export interface ExecutionResult {
  id: string;
  cape_id: string;
  cape_name: string;
  status: ExecutionStatus;
  inputs: Record<string, unknown>;
  output?: unknown;
  error?: string;
  execution_time_ms: number;
  tokens_used?: number;
  cost_usd?: number;
  steps_executed?: string[];
  started_at: string;
  completed_at?: string;
}

export interface SystemStats {
  total_capes: number;
  total_packs: number;
  total_executions: number;
  success_rate: number;
  avg_execution_time: number;
  total_tokens: number;
  total_cost: number;
  by_pack: Record<string, number>;
}

// Pack types
export interface Pack {
  name: string;
  display_name: string;
  description: string;
  version: string;
  icon?: string;
  color?: string;
  target_users: string[];
  scenarios: string[];
  cape_ids: string[];
  cape_count: number;
}

export interface PackDetail extends Pack {
  capes: Cape[];
}

export interface PacksResponse {
  packs: Pack[];
  total_packs: number;
  total_capes_in_packs: number;
}

// File types
export type FileStatus = "uploaded" | "processing" | "completed" | "expired" | "deleted";

export interface FileInfo {
  file_id: string;
  original_name: string;
  content_type: string;
  size_bytes: number;
  status: FileStatus;
  session_id?: string;
  created_at: string;
  expires_at: string;
  cape_id?: string;
  is_output: boolean;
  download_url: string;
}

export interface UploadResponse {
  files: FileInfo[];
  session_id: string;
  total_size_bytes: number;
}

export interface SessionFilesResponse {
  session_id: string;
  files: FileInfo[];
  total_files: number;
  total_size_bytes: number;
}

export interface ProcessResponse {
  success: boolean;
  input_file: FileInfo;
  output_files: FileInfo[];
  execution_time_ms: number;
  error?: string;
  cape_id: string;
  session_id: string;
}

export interface StorageStats {
  total_files: number;
  total_sessions: number;
  total_size_mb: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
}
