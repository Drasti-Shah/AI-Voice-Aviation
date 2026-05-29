"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, fmtTime, type Campaign } from "@/lib/api";

export default function CampaignDetailPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const [camp, setCamp] = useState<Campaign | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const tick = async () => {
      try {
        const c = await api.campaign(id);
        setCamp(c);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    };
    tick();
    const iv = setInterval(tick, 2500);
    return () => clearInterval(iv);
  }, [id]);

  async function pause() {
    if (!camp) return;
    setCamp(await api.pauseCampaign(camp.id));
  }
  async function resume() {
    if (!camp) return;
    setCamp(await api.resumeCampaign(camp.id));
  }

  if (error) {
    return (
      <div className="p-8">
        <Link href="/campaigns" className="text-sm text-blue-600 hover:underline">
          ← Back
        </Link>
        <p className="mt-4 text-rose-600">{error}</p>
      </div>
    );
  }

  if (!camp) return <div className="p-8 text-slate-500">Loading…</div>;

  const pct = camp.numbers.length === 0 ? 0 : Math.round((camp.cursor / camp.numbers.length) * 100);

  return (
    <div className="p-8 max-w-5xl">
      <Link href="/campaigns" className="text-sm text-blue-600 hover:underline">
        ← Back to campaigns
      </Link>
      <div className="flex items-start justify-between mt-2 mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">{camp.name}</h1>
          <p className="text-slate-500 text-sm">
            {fmtTime(camp.created)} · {camp.numbers.length} numbers · status:{" "}
            <span className="font-medium">{camp.status}</span>
          </p>
        </div>
        <div className="flex gap-2">
          {camp.status === "running" && (
            <button onClick={pause} className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-sm rounded">
              Pause
            </button>
          )}
          {camp.status === "paused" && (
            <button onClick={resume} className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm rounded">
              Resume
            </button>
          )}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6 shadow-sm">
        <div className="flex items-center justify-between mb-2 text-sm">
          <span className="font-medium">Progress</span>
          <span className="text-slate-500">
            {camp.cursor} / {camp.numbers.length} ({pct}%)
          </span>
        </div>
        <div className="bg-slate-200 rounded-full h-3 overflow-hidden">
          <div
            className="bg-blue-500 h-3 rounded-full transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-200">
          <h2 className="font-semibold">Calls</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2 text-left">To</th>
              <th className="px-4 py-2 text-left">Twilio status</th>
              <th className="px-4 py-2 text-left">Our status</th>
              <th className="px-4 py-2 text-right">Duration</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {camp.calls.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-400">
                  No calls placed yet
                </td>
              </tr>
            ) : (
              camp.calls.map((c, i) => (
                <tr key={i}>
                  <td className="px-4 py-2 font-medium">{c.to}</td>
                  <td className="px-4 py-2">
                    <span className="text-xs px-2 py-1 rounded bg-slate-100">{c.status}</span>
                  </td>
                  <td className="px-4 py-2 text-slate-500">{c.meta?.status ?? "—"}</td>
                  <td className="px-4 py-2 text-right">{c.meta?.duration ?? 0}s</td>
                  <td className="px-4 py-2 text-right">
                    {c.sid && (
                      <Link href={`/calls/${c.sid}`} className="text-blue-600 hover:text-blue-800 text-sm">
                        Detail →
                      </Link>
                    )}
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
