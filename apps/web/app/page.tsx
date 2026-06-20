import Link from "next/link";

const invariants = [
  "Tenant isolation",
  "Deletion guarantee",
  "Provenance on every memory",
  "Graceful degradation",
  "Policy-before-storage",
  "Temporary chat writes nothing",
  "Append-only audit",
];

export default function Home() {
  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <span className="chip border-accent text-accent">Enterprise memory governance</span>
        <h1 className="text-4xl font-bold text-white">
          Memory is not a database. It is governed state.
        </h1>
        <p className="max-w-3xl text-slate-400">
          MemoryOps AI is an enterprise-shaped memory governance layer for AI assistants. It
          implements a ChatGPT-style memory lifecycle — capture, policy evaluation, typed storage,
          hybrid retrieval, controlled forgetting, auditability, and tenant isolation. Most demos
          treat memory as a vector store. MemoryOps AI treats memory as governed state.
        </p>
        <div className="flex gap-3">
          <Link href="/chat" className="btn">
            Try the chat demo
          </Link>
          <Link href="/architecture" className="btn bg-slate-700">
            See the architecture
          </Link>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="card">
          <h3 className="font-semibold text-white">Write path</h3>
          <p className="mt-2 text-sm text-slate-400">
            Gateway → Extractor → Policy Broker → Write Service → Typed Store → Audit. Nothing is
            stored without an explicit, audited policy decision.
          </p>
        </div>
        <div className="card">
          <h3 className="font-semibold text-white">Read path</h3>
          <p className="mt-2 text-sm text-slate-400">
            Retriever → Ranker → Context Composer → Response. Hybrid retrieval with explainable
            memory-used badges; failures degrade gracefully.
          </p>
        </div>
        <div className="card">
          <h3 className="font-semibold text-white">Governance planes</h3>
          <p className="mt-2 text-sm text-slate-400">
            Security, Governance, Observability, Reliability, and Evaluation wrap all five verbs:
            capture, store, retrieve, update, forget.
          </p>
        </div>
      </section>

      <section className="card">
        <h3 className="font-semibold text-white">Guarantees enforced in code + tests</h3>
        <div className="mt-3 flex flex-wrap gap-2">
          {invariants.map((i) => (
            <span key={i} className="chip">
              ✓ {i}
            </span>
          ))}
        </div>
      </section>
    </div>
  );
}
