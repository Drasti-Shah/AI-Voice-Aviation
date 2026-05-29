"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, fmtAgo, type DashboardData, type CallMeta, type Turn } from "@/lib/api";

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardData | null>(null);
  const [calls, setCalls] = useState<CallMeta[]>([]);
  const [liveTurns, setLiveTurns] = useState<Turn[]>([]);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const [s, c, t] = await Promise.all([api.dashboard(), api.calls(), api.transcript()]);
        if (!cancelled) {
          setStats(s);
          setCalls(c.calls);
          setLiveTurns(t.turns);
        }
      } catch {}
    };
    tick();
    const id = setInterval(tick, 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const statCards = stats
    ? [
        { label: "Total calls", value: stats.total_calls, color: "text-slate-700" },
        { label: "Active now", value: stats.active_calls, color: "text-emerald-600" },
        { label: "Completed", value: stats.completed_calls, color: "text-blue-600" },
        { label: "Avg duration", value: `${stats.avg_duration_s}s`, color: "text-slate-700" },
      ]
    : [];

  return (
    <div className="p-8 max-w-6xl">
      <h1 className="text-2xl font-bold mb-1">Dashboard</h1>
      <p className="text-slate-500 mb-6">Real-time view of call activity</p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {statCards.map((c) => (
          <div key={c.label} className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="text-xs uppercase tracking-wide text-slate-400">{c.label}</div>
            <div className={`text-3xl font-bold mt-1 ${c.color}`}>{c.value}</div>
          </div>
        ))}
      </div>

      {stats?.active_call_sid && (
        <div className="bg-white rounded-xl border border-emerald-200 mb-8 shadow-sm">
          <div className="px-5 py-3 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="font-semibold">Live call in progress</span>
            </div>
            <Link
              href={`/calls/${stats.active_call_sid}`}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Open detail →
            </Link>
          </div>
          <div className="px-5 py-4 max-h-72 overflow-y-auto space-y-1.5 font-mono text-sm">
            {liveTurns.length === 0 ? (
              <p className="text-slate-400">(no turns yet)</p>
            ) : (
              liveTurns.map((t, i) => (
                <div key={i} className="flex gap-2">
                  <span
                    className={`shrink-0 font-bold ${
                      t.role === "user"
                        ? "text-emerald-700"
                        : t.role === "bot"
                        ? "text-blue-700"
                        : "text-slate-400"
                    }`}
                  >
                    {t.role === "user" ? "USER:" : t.role === "bot" ? "BOT:" : "···"}
                  </span>
                  <span className="whitespace-pre-wrap">{t.text}</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="px-5 py-3 border-b border-slate-200 flex items-center justify-between">
          <h2 className="font-semibold">Recent calls</h2>
          <Link href="/calls" className="text-sm text-blue-600 hover:text-blue-800">
            View all →
          </Link>
        </div>
        <div className="divide-y divide-slate-100">
          {calls.length === 0 ? (
            <div className="px-5 py-8 text-slate-400 text-center">
              No calls yet. Try the <Link href="/dial" className="text-blue-600 hover:underline">Dial</Link> page.
            </div>
          ) : (
            calls.slice(0, 5).map((c) => (
              <Link
                key={c.sid}
                href={`/calls/${c.sid}`}
                className="flex items-center justify-between px-5 py-3 hover:bg-slate-50"
              >
                <div>
                  <div className="font-medium">{c.to}</div>
                  <div className="text-xs text-slate-500">{fmtAgo(c.created)}</div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs px-2 py-1 rounded bg-slate-100 text-slate-700">
                    {c.status || "?"}
                  </span>
                  <span className="text-xs text-slate-500">{c.duration ?? 0}s</span>
                  <span className="text-xs text-slate-500">{c.turn_count ?? 0} turns</span>
                </div>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
