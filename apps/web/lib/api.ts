// Thin API client for the MemoryOps AI backend.

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Demo identity. In production these come from auth/session.
export const DEMO_TENANT = "tenant_demo";
export const DEMO_USER = "user_demo";

export type Decision =
  | "SAVE"
  | "PENDING_APPROVAL"
  | "BLOCK"
  | "DROP_LOW_UTILITY"
  | "MERGE_WITH_EXISTING"
  | "UPDATE_EXISTING";

export interface CandidateDecision {
  content: string;
  decision: Decision;
  type: string;
  confidence: number;
  importance: number;
  sensitivity: string;
  reason: string;
  memory_id?: string | null;
}

export interface ScoreBreakdown {
  vector_similarity: number;
  keyword_score: number;
  importance_score: number;
  confidence: number;
  recency: number;
  reinforcement: number;
}

export type RetrievalMode = "hybrid" | "fallback" | "none";

export interface UsedMemory {
  memory_id: string;
  content: string;
  memory_type?: string;
  score: number;
  score_breakdown?: Partial<ScoreBreakdown>;
  reason: string;
  source?: { kind: string; excerpt: string };
}

export interface ChatResponse {
  assistant_message: string;
  used_memories: UsedMemory[];
  candidate_memories: CandidateDecision[];
  audit_event_ids: string[];
  temporary_chat: boolean;
  retrieval_mode?: RetrievalMode;
  trace_id: string;
}

export interface MemoryRecord {
  id: string;
  tenant_id: string;
  user_id: string;
  memory_type: string;
  content: string;
  importance: number;
  confidence: number;
  sensitivity: string;
  status: string;
  source: { kind: string; excerpt: string };
  reinforcement_count: number;
  created_at: string;
  updated_at: string;
}

export interface AuditEvent {
  id: string;
  action: string;
  reason: string;
  memory_id?: string | null;
  trace_id?: string | null;
  created_at: string;
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "content-type": "application/json" },
    cache: "no-store",
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  chat: (message: string, temporary_chat = false) =>
    http<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        tenant_id: DEMO_TENANT,
        user_id: DEMO_USER,
        message,
        temporary_chat,
      }),
    }),

  memories: (status?: string) =>
    http<MemoryRecord[]>(
      `/api/memories?tenant_id=${DEMO_TENANT}&user_id=${DEMO_USER}` +
        (status ? `&status=${status}` : "")
    ),

  patchMemory: (id: string, patch: Record<string, unknown>) =>
    http<MemoryRecord>(`/api/memories/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ tenant_id: DEMO_TENANT, user_id: DEMO_USER, ...patch }),
    }),

  deleteMemory: (id: string) =>
    http<{ id: string; status: string }>(`/api/memories/${id}`, {
      method: "DELETE",
      body: JSON.stringify({ tenant_id: DEMO_TENANT, user_id: DEMO_USER }),
    }),

  audit: () => http<AuditEvent[]>(`/api/audit?tenant_id=${DEMO_TENANT}`),

  metrics: () =>
    http<{
      total_memories: number;
      by_status: Record<string, number>;
      audit_events: number;
      by_action: Record<string, number>;
    }>(`/api/metrics?tenant_id=${DEMO_TENANT}`),

  runEvals: () =>
    http<{ total: number; passed: number; failed: number; pass_rate: number }>(
      "/api/evals/run",
      { method: "POST" }
    ),

  ready: () =>
    http<{
      ready: boolean;
      storage: string;
      llm_provider: string;
      embeddings_provider: string;
      embedding_dim: number;
      detail: string;
    }>("/readyz"),
};
