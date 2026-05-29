"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, fmtTime, type Campaign } from "@/lib/api";

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);

  useEffect(() => {
    const tick = async () => {
      try {
        const r = await api.campaigns();
        setCampaigns(r.campaigns);
      } catch {}
    };
    tick();
    const id = setInterval(tick, 3000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="p-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">Campaigns</h1>
          <p className="text-slate-500">Bulk-call list of numbers (CSV upload supported)</p>
        </div>
        <Link
          href="/campaigns/new"
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold"
        >
          + New campaign
        </Link>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3 text-left">Name</th>
              <th className="px-4 py-3 text-left">Created</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-right">Progress</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-sm">
            {campaigns.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-slate-400">
                  No campaigns yet —{" "}
                  <Link href="/campaigns/new" className="text-blue-600 hover:underline">
                    create one
                  </Link>
                </td>
              </tr>
            ) : (
              campaigns.map((c) => {
                const pct = c.numbers.length === 0 ? 0 : Math.round((c.cursor / c.numbers.length) * 100);
                return (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium">{c.name}</td>
                    <td className="px-4 py-3 text-slate-600">{fmtTime(c.created)}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-1 rounded font-medium ${statusClass(c.status)}`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex items-center gap-2">
                        <div className="w-24 bg-slate-200 rounded-full h-2">
                          <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${pct}%` }} />
                        </div>
                        <span className="text-xs text-slate-500">
                          {c.cursor}/{c.numbers.length}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link href={`/campaigns/${c.id}`} className="text-blue-600 hover:text-blue-800">
                        View →
                      </Link>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function statusClass(s: string) {
  if (s === "running") return "bg-emerald-100 text-emerald-800";
  if (s === "paused") return "bg-amber-100 text-amber-800";
  if (s === "completed") return "bg-blue-100 text-blue-800";
  return "bg-slate-100 text-slate-700";
}
