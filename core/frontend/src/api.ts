export interface AgentEntry {
  path: string;
  name: string;
  description: string;
  category: string;
  node_count: number;
  tool_count: number;
  is_loaded: boolean;
  supervisor?: boolean;
  supervisor_name?: string;
  department?: string;
  role_title?: string;
}

export interface DiscoverResponse {
  templates: AgentEntry[];
  supervisors: AgentEntry[];
  exports: AgentEntry[];
}

export interface SessionSummary {
  session_id: string;
  agent_path: string;
  name: string;
  description: string;
  goal?: string;
  waiting_for_input: boolean;
  current_exec_id: string | null;
  supervised?: boolean;
  supervisor_mode?: string;
  input_graph_id?: string | null;
  supervisor?: boolean;
  supervisor_name?: string;
  department?: string;
  role_title?: string;
}

export interface SessionDetail extends SessionSummary {
  nodes: Array<{ id: string; name: string; description?: string }>;
  edges: Array<{ id: string; source: string; target: string }>;
  entry_points: Array<{ id: string; name: string; entry_node: string }>;
  intro_message?: string;
  worker_nodes?: Array<{ id: string; name: string; description?: string }>;
  worker_edges?: Array<{ id: string; source: string; target: string }>;
}

export interface TaskRecord {
  id: number;
  subject: string;
  description: string;
  active_form?: string | null;
  owner?: string | null;
  status: "pending" | "in_progress" | "completed";
  blocks: number[];
  blocked_by: number[];
}

export interface ModelCatalogResponse {
  model: string;
  catalog: Record<string, Array<Record<string, unknown>>>;
  defaults: Record<string, string>;
  presets: Record<string, Record<string, unknown>>;
}

export interface CheckpointSummary {
  checkpoint_id: string;
  checkpoint_type: string;
  created_at: string;
  current_node: string;
  description: string;
  is_clean: boolean;
}

export interface ExecutionSummary {
  execution_id: string;
  checkpoint_count: number;
  latest_checkpoint_id: string | null;
}

export interface OpsRun {
  agent: string;
  execution_id: string;
  status: string;
  started_at?: string;
  ended_at?: string;
  total_tokens: number;
  total_input_tokens?: number;
  total_output_tokens?: number;
  estimated_cost_usd: number;
  checkpoint_count: number;
  latest_checkpoint_id?: string | null;
  error?: string;
}

export interface OpsAlert {
  severity: string;
  title: string;
  message: string;
  timestamp?: string;
  execution_id?: string;
  agent?: string;
}

export interface AgentEvent {
  type: string;
  stream_id: string;
  node_id: string | null;
  execution_id: string | null;
  data: Record<string, unknown>;
  timestamp: string;
  graph_id?: string | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message = (body as { error?: string; message?: string }).message
      || (body as { error?: string }).error
      || res.statusText;
    throw new Error(message);
  }
  return body as T;
}

export const api = {
  discover: () => request<DiscoverResponse>("/discover"),
  getConfig: () => request<ModelCatalogResponse>("/config"),
  listSessions: () => request<{ sessions: SessionSummary[] }>("/sessions"),
  createSession: (agentPath: string, model?: string) =>
    request<SessionSummary>("/sessions", {
      method: "POST",
      body: JSON.stringify({ agent_path: agentPath, model }),
    }),
  getSession: (sessionId: string) => request<SessionDetail>(`/sessions/${sessionId}`),
  sendMessage: (sessionId: string, message: string) =>
    request<{ action: string; execution_id?: string }>(`/sessions/${sessionId}/message`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  deleteSession: (sessionId: string) =>
    request<{ stopped: boolean }>(`/sessions/${sessionId}`, { method: "DELETE" }),
  pauseSession: (sessionId: string) =>
    request<{ paused: boolean; session_id: string }>(`/sessions/${sessionId}/pause`, {
      method: "POST",
    }),
  resumeSession: (sessionId: string) =>
    request<{ resumed: boolean; session_id: string; execution_id?: string }>(
      `/sessions/${sessionId}/resume`,
      { method: "POST" },
    ),
  listExecutions: (sessionId: string) =>
    request<{ executions: ExecutionSummary[] }>(`/sessions/${sessionId}/executions`),
  listCheckpoints: (sessionId: string, executionId: string) =>
    request<{ execution_id: string; checkpoints: CheckpointSummary[] }>(
      `/sessions/${sessionId}/executions/${executionId}/checkpoints`,
    ),
  resumeFromCheckpoint: (sessionId: string, executionId: string, checkpointId: string) =>
    request<{ resumed: boolean; session_id: string; execution_id: string; checkpoint_id: string }>(
      `/sessions/${sessionId}/executions/${executionId}/checkpoints/${checkpointId}/resume`,
      { method: "POST" },
    ),
  getOpsSummary: () => request<{ metrics: Record<string, unknown>; otel: Record<string, unknown> }>("/ops/summary"),
  getOpsRuns: () => request<{ runs: OpsRun[]; count: number }>("/ops/runs"),
  getOpsAlerts: () => request<{ alerts: OpsAlert[]; count: number }>("/ops/alerts"),
  getSessionTasks: (sessionId: string, supervisor = false) =>
    request<{ task_list_id: string | null; tasks: TaskRecord[] }>(
      `/sessions/${sessionId}/tasks${supervisor ? "?supervisor=true" : ""}`,
    ),
  patchTask: (
    taskListId: string,
    taskId: number,
    body: Partial<Pick<TaskRecord, "status" | "subject" | "description">>,
  ) =>
    request<{ task: TaskRecord }>(`/tasks/${encodeURIComponent(taskListId)}/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
};
