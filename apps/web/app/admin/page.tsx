"use client";

import { useEffect, useState } from "react";
import { api, AuditEvent } from "@/lib/api";

type Metrics = Awaited<ReturnType<typeof api.metrics>>;

export default function AdminPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [evals, setEvals] = useState<{ passed: number; total: number; pass_rate: number } | null>(
    null
  );
  const [error, setError] = useState("");

  async function load() {
    try {
      const [m, a] = await Promise.all([api.metrics(), api.audit()]);
      setMetrics(m);
      setAudit(a);
      setError("");
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    load();
  }, []);

  const cards = metrics
    ? [
        { label: "Total memories", value: metrics.total_memories },
        { label: "Active", value: metrics.by_status.active ?? 0 },
        { label: "Pending", value: metrics.by_status.pending ?? 0 },
        { label: "Blocked", value: metrics.by_action.memory_blocked ?? 0 },
        { label: "Deleted", value: metrics.by_status.deleted ?? 0 },
        { label: "Retrievals", value: metrics.by_action.memory_retrieved ?? 0 },
        { label: "Audit events", value: metrics.audit_events },
      ]
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Admin & audit</h1>
        <button
          className="btn"
          onClick={async () => setEvals(await api.runEvals())}
        >
          Run evals
        </button>
      </div>
      {error && <p className="text-sm text-rose-400">API error: {error}</p>}

      {evals && (
        <div className="card">
          <span className="chip border-emerald-600 text-emerald-400">
            evals {evals.passed}/{evals.total} passed · {(evals.pass_rate * 100).toFixed(0)}%
          </span>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {cards.map((c) => (
          <div key={c.label} className="card">
            <p className="text-xs uppercase tracking-wide text-slate-500">{c.label}</p>
            <p className="mt-1 text-2xl font-bold text-white">{c.value}</p>
          </div>
        ))}
      </div>

      <div className="card">
        <h2 className="mb-3 font-semibold text-white">Audit log (append-only)</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="p-2">When</th>
                <th className="p-2">Action</th>
                <th className="p-2">Reason</th>
                <th className="p-2">Trace</th>
              </tr>
            </thead>
            <tbody>
              {audit.map((e) => (
                <tr key={e.id} className="border-t border-slate-800">
                  <td className="whitespace-nowrap p-2 text-slate-500">
                    {new Date(e.created_at).toLocaleTimeString()}
                  </td>
                  <td className="p-2">
                    <span className="chip">{e.action}</span>
                  </td>
                  <td className="p-2 text-slate-400">{e.reason}</td>
                  <td className="p-2 text-slate-600">{e.trace_id?.slice(0, 8)}</td>
                </tr>
              ))}
              {audit.length === 0 && (
                <tr>
                  <td className="p-2 text-slate-500" colSpan={4}>
                    No audit events yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
