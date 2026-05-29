"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, fmtTime, type CallMeta } from "@/lib/api";

export default function CallsPage() {
  const [calls, setCalls] = useState<CallMeta[]>([]);

  useEffect(() => {
    const tick = async () => {
      try {
        const r = await api.calls();
        setCalls(r.calls);
      } catch {}
    };
    tick();
    const id = setInterval(tick, 3000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="p-8 max-w-6xl">
      <h1 className="text-2xl font-bold mb-1">Calls</h1>
      <p className="text-slate-500 mb-6">Every call placed this session — click for full transcript & recording</p>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3 text-left">When</th>
              <th className="px-4 py-3 text-left">To</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-right">Duration</th>
              <th className="px-4 py-3 text-right">Turns</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-sm">
            {calls.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-slate-400">
                  No calls yet
                </td>
              </tr>
            ) : (
              calls.map((c) => (
                <tr key={c.sid} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-slate-600">{fmtTime(c.created)}</td>
                  <td className="px-4 py-3 font-medium">{c.to}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs px-2 py-1 rounded bg-slate-100 text-slate-700">
                      {c.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">{c.duration ?? 0}s</td>
                  <td className="px-4 py-3 text-right">
                    {c.user_turns}u / {c.bot_turns}b
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link href={`/calls/${c.sid}`} className="text-blue-600 hover:text-blue-800">
                      View →
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
