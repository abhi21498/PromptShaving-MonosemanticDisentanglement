"use client";

import { useEffect, useState } from "react";
import { api, MemoryRecord } from "@/lib/api";

export default function MemoriesPage() {
  const [rows, setRows] = useState<MemoryRecord[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      setRows(await api.memories());
      setError("");
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function act(id: string, fn: () => Promise<unknown>) {
    await fn();
    await load();
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Memory dashboard</h1>
      {error && <p className="text-sm text-rose-400">API error: {error}</p>}
      {loading && <p className="text-sm text-slate-400">Loading…</p>}

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="p-2">Content</th>
              <th className="p-2">Type</th>
              <th className="p-2">Sensitivity</th>
              <th className="p-2">Imp.</th>
              <th className="p-2">Conf.</th>
              <th className="p-2">Status</th>
              <th className="p-2">Source</th>
              <th className="p-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((m) => (
              <tr key={m.id} className="border-t border-slate-800 align-top">
                <td className="max-w-xs p-2">{m.content}</td>
                <td className="p-2">{m.memory_type}</td>
                <td className="p-2">{m.sensitivity}</td>
                <td className="p-2">{m.importance}</td>
                <td className="p-2">{m.confidence.toFixed(2)}</td>
                <td className="p-2">
                  <span className="chip">{m.status}</span>
                </td>
                <td className="max-w-[10rem] truncate p-2 text-slate-500" title={m.source.excerpt}>
                  {m.source.kind}
                </td>
                <td className="space-x-2 whitespace-nowrap p-2">
                  {m.status === "pending" && (
                    <>
                      <button
                        className="text-emerald-400 hover:underline"
                        onClick={() => act(m.id, () => api.patchMemory(m.id, { status: "active" }))}
                      >
                        approve
                      </button>
                      <button
                        className="text-rose-400 hover:underline"
                        onClick={() => act(m.id, () => api.patchMemory(m.id, { status: "rejected" }))}
                      >
                        reject
                      </button>
                    </>
                  )}
                  <button
                    className="text-slate-400 hover:underline"
                    onClick={() => act(m.id, () => api.patchMemory(m.id, { status: "archived" }))}
                  >
                    archive
                  </button>
                  <button
                    className="text-rose-400 hover:underline"
                    onClick={() => act(m.id, () => api.deleteMemory(m.id))}
                  >
                    delete
                  </button>
                </td>
              </tr>
            ))}
            {!loading && rows.length === 0 && (
              <tr>
                <td className="p-2 text-slate-500" colSpan={8}>
                  No memories yet. Try the chat demo.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
