"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

export default function NewCampaignPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [numbers, setNumbers] = useState<string[]>([]);
  const [manualText, setManualText] = useState("");
  const [uploading, setUploading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setUploading(true);
    setError(null);
    try {
      const r = await api.uploadCsv(f);
      setNumbers(r.numbers);
      if (!name) setName(f.name.replace(/\.csv$/i, ""));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
    }
  }

  function parseManual() {
    const parsed = manualText
      .split(/[\n,]+/)
      .map((s) => s.trim())
      .filter(Boolean)
      .map((s) => {
        if (s.startsWith("+")) return s;
        if (/^\d{10}$/.test(s)) return "+91" + s;
        return null;
      })
      .filter((s): s is string => s !== null);
    setNumbers(parsed);
  }

  async function start() {
    if (numbers.length === 0) {
      setError("No valid numbers");
      return;
    }
    setStarting(true);
    setError(null);
    try {
      const camp = await api.createCampaign(name || "Untitled campaign", numbers);
      router.push(`/campaigns/${camp.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStarting(false);
    }
  }

  return (
    <div className="p-8 max-w-3xl">
      <Link href="/campaigns" className="text-sm text-blue-600 hover:underline">
        ← Back to campaigns
      </Link>
      <h1 className="text-2xl font-bold mt-2 mb-1">New campaign</h1>
      <p className="text-slate-500 mb-6">Upload a CSV of phone numbers or paste them manually</p>

      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6 shadow-sm space-y-5">
        <div>
          <label className="block text-sm font-medium mb-1">Campaign name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Diwali greetings"
            className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Upload CSV</label>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={onFile}
            className="block text-sm"
          />
          <p className="text-xs text-slate-500 mt-1">
            CSV with a <code>phone</code> column, or one number per line. 10-digit Indian numbers are auto-prefixed with +91.
          </p>
          {uploading && <p className="text-sm text-slate-500 mt-2">Uploading…</p>}
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Or paste numbers (comma or newline separated)</label>
          <textarea
            value={manualText}
            onChange={(e) => setManualText(e.target.value)}
            placeholder="+919978256935&#10;+917990267016&#10;9724556935"
            rows={4}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={parseManual}
            type="button"
            className="mt-2 text-sm text-blue-600 hover:text-blue-800"
          >
            Parse →
          </button>
        </div>
      </div>

      {numbers.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6 shadow-sm">
          <div className="text-sm font-medium mb-3">
            {numbers.length} number{numbers.length === 1 ? "" : "s"} ready to call
          </div>
          <div className="max-h-48 overflow-y-auto bg-slate-50 rounded p-3 font-mono text-xs space-y-0.5">
            {numbers.map((n, i) => (
              <div key={i}>{n}</div>
            ))}
          </div>
        </div>
      )}

      {error && <p className="text-rose-600 text-sm mb-4">{error}</p>}

      <button
        onClick={start}
        disabled={starting || numbers.length === 0}
        className="px-6 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white font-semibold rounded-lg"
      >
        {starting ? "Starting…" : `Start campaign (${numbers.length} calls)`}
      </button>
    </div>
  );
}
