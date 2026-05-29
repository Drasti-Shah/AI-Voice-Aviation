"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, fmtTime, type Turn, type CallMeta } from "@/lib/api";

export default function CallDetailPage({ params }: { params: { sid: string } }) {
  const { sid } = params;
  const [meta, setMeta] = useState<CallMeta | null>(null);
  const [metrics, setMetrics] = useState<any>({});
  const [turns, setTurns] = useState<Turn[]>([]);
  const [recordingError, setRecordingError] = useState(false);

  useEffect(() => {
    const tick = async () => {
      try {
        const data = await api.callTranscript(sid);
        setMeta(data.meta);
        setMetrics(data.metrics || {});
        setTurns(data.turns);
      } catch {}
    };
    tick();
    const id = setInterval(tick, 2000);
    return () => clearInterval(id);
  }, [sid]);

  // Latency: time between consecutive user→bot turns (when transcript has timestamps)
  const responseLatencies: number[] = [];
  for (let i = 0; i < turns.length - 1; i++) {
    if (turns[i].role === "user" && turns[i + 1].role === "bot") {
      responseLatencies.push(turns[i + 1].ts - turns[i].ts);
    }
  }
  const avgLatency =
    responseLatencies.length > 0
      ? (responseLatencies.reduce((a, b) => a + b, 0) / responseLatencies.length).toFixed(1)
      : "—";

  return (
    <div className="p-8 max-w-5xl">
      <Link href="/calls" className="text-sm text-blue-600 hover:underline">
        ← Back to calls
      </Link>
      <h1 className="text-2xl font-bold mt-2 mb-1">Call detail</h1>
      <p className="text-slate-500 text-sm font-mono mb-6">{sid}</p>

      <div className="grid md:grid-cols-4 gap-4 mb-6">
        <Metric label="To" value={meta?.to ?? "—"} />
        <Metric label="Status" value={meta?.status ?? "—"} />
        <Metric label="Duration" value={`${meta?.duration ?? 0}s`} />
        <Metric label="Started" value={meta?.started ? fmtTime(meta.started) : "—"} small />
      </div>

      <div className="grid md:grid-cols-4 gap-4 mb-8">
        <Metric label="Total turns" value={`${(metrics.user_turns ?? 0) + (metrics.bot_turns ?? 0)}`} />
        <Metric label="User turns" value={metrics.user_turns ?? 0} />
        <Metric label="Bot turns" value={metrics.bot_turns ?? 0} />
        <Metric label="Avg response" value={`${avgLatency}s`} />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6 shadow-sm">
        <h2 className="font-semibold mb-3">Recording</h2>
        {meta?.status === "completed" || meta?.status === "in-progress" ? (
          <div>
            <audio
              controls
              className="w-full"
              src={api.recordingUrl(sid)}
              onError={() => setRecordingError(true)}
            />
            {recordingError && (
              <p className="text-xs text-slate-500 mt-2">
                Recording may still be processing — refresh in 30 seconds.
              </p>
            )}
          </div>
        ) : (
          <p className="text-slate-400 text-sm">Recording available once call completes</p>
        )}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="px-5 py-3 border-b border-slate-200">
          <h2 className="font-semibold">Full transcript ({turns.length} turns)</h2>
        </div>
        <div className="px-5 py-4 max-h-[500px] overflow-y-auto space-y-2 font-mono text-sm">
          {turns.length === 0 ? (
            <p className="text-slate-400">(no transcript)</p>
          ) : (
            turns.map((t, i) => (
              <div key={i} className="flex gap-3 items-start">
                <span className="shrink-0 text-xs text-slate-400 w-16 pt-0.5">
                  {new Date(t.ts * 1000).toLocaleTimeString("en-US", { hour12: false })}
                </span>
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
    </div>
  );
}

function Metric({ label, value, small }: { label: string; value: React.ReactNode; small?: boolean }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className={`font-bold mt-1 ${small ? "text-sm" : "text-xl"}`}>{value}</div>
    </div>
  );
}
