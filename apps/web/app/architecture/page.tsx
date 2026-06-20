const sections = [
  {
    title: "Write path",
    body: "Gateway → Extractor → Policy Broker → Write Service → Typed Store → Audit. The policy broker is the choke point: secrets are blocked, sensitive content goes to an approval queue, low-utility is dropped, duplicates reinforce existing memory. Nothing is stored without an audited decision.",
  },
  {
    title: "Read path",
    body: "Retriever (hybrid: vector + keyword) → Ranker (0.35 semantic + 0.20 keyword + 0.15 importance + 0.10 recency + 0.10 confidence + 0.10 reinforcement) → Context Composer → Response. Deleted and pending memories are never retrieved. Retrieval failures degrade gracefully.",
  },
  {
    title: "Background jobs",
    body: "Decay ages out memory weights, archival retires low-weight memories, conflict resolution reconciles contradictions, reflection/compression collapses repeats. Jobs share the repository interface so they can move to Celery/Temporal.",
  },
  {
    title: "Security plane",
    body: "Tenant + user scoping on every query, RLS-ready schema, secret/PII detection, prompt-injection guard, temporary chat, soft-delete with a retrieval-exclusion guarantee.",
  },
  {
    title: "Governance plane",
    body: "Typed lifecycle states, approve/reject/edit/archive/delete, append-only audit, provenance on every memory, explainable memory-used badges.",
  },
  {
    title: "Observability plane",
    body: "Structured JSON logs with per-request trace_id and secret redaction, latency + memory counts, metrics surfaced on the admin dashboard. OpenTelemetry / Prometheus / Langfuse on the roadmap.",
  },
];

const invariants = [
  "User A's memory is never returned to User B or another tenant.",
  "Deleted memories are never retrieved again.",
  "Every stored memory traces back to its source.",
  "Memory retrieval failure never blocks a response.",
  "Unsafe / secret-like content is filtered before storage.",
  "Temporary sessions never write or retrieve memory.",
  "Every lifecycle event produces an append-only audit event.",
];

export default function ArchitecturePage() {
  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-white">Architecture</h1>

      <div className="grid gap-4 md:grid-cols-2">
        {sections.map((s) => (
          <div key={s.title} className="card">
            <h2 className="font-semibold text-white">{s.title}</h2>
            <p className="mt-2 text-sm text-slate-400">{s.body}</p>
          </div>
        ))}
      </div>

      <div className="card">
        <h2 className="font-semibold text-white">Enterprise invariants</h2>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-400">
          {invariants.map((i) => (
            <li key={i}>{i}</li>
          ))}
        </ul>
      </div>

      <div className="card">
        <h2 className="font-semibold text-white">Production upgrade path</h2>
        <p className="mt-2 text-sm text-slate-400">
          Heuristic LLM/embeddings → provider adapters. RLS enabled → enforced. Soft delete →
          crypto-shred retention worker. Logs → OpenTelemetry traces + Prometheus metrics + Langfuse.
          In-memory store → Postgres + pgvector. Loop worker → Celery/Temporal with retries + DLQs.
        </p>
      </div>
    </div>
  );
}
