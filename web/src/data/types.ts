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
  total_executions: number;
  success_rate: number;
  avg_execution_time: number;
  total_tokens: number;
  total_cost: number;
}
