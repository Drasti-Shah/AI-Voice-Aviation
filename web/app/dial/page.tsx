"use client";

import { useEffect, useRef, useState } from "react";
import { api, type Turn } from "@/lib/api";

const KEYPAD = [
  ["1", "2", "3"],
  ["4", "5", "6"],
  ["7", "8", "9"],
  ["*", "0", "#"],
];

export default function DialPage() {
  const [phone, setPhone] = useState("+919978256935");
  const [calling, setCalling] = useState(false);
  const [callSid, setCallSid] = useState<string | null>(null);
  const [callStatus, setCallStatus] = useState<string>("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [error, setError] = useState<string | null>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const id = setInterval(async () => {
      try {
        const t = await api.transcript();
        setTurns(t.turns);
      } catch {}
    }, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!callSid) return;
    if (callStatus === "completed" || callStatus === "failed" || callStatus === "canceled") return;
    const id = setInterval(async () => {
      try {
        const s = await api.callStatus(callSid);
        setCallStatus(s.status);
      } catch {}
    }, 2000);
    return () => clearInterval(id);
  }, [callSid, callStatus]);

  useEffect(() => {
    transcriptRef.current?.scrollTo({ top: transcriptRef.current.scrollHeight, behavior: "smooth" });
  }, [turns]);

  const press = (k: string) => setPhone((p) => p + k);
  const backspace = () => setPhone((p) => p.slice(0, -1));

  async function placeCall(e?: React.FormEvent) {
    e?.preventDefault();
    setError(null);
    if (!phone.startsWith("+")) {
      setError("Number must be E.164 (start with '+')");
      return;
    }
    setCalling(true);
    try {
      const r = await api.call(phone);
      setCallSid(r.sid);
      setCallStatus(r.status);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCalling(false);
    }
  }

  const statusColor: Record<string, string> = {
    queued: "bg-amber-100 text-amber-800",
    ringing: "bg-amber-100 text-amber-800",
    "in-progress": "bg-emerald-100 text-emerald-800",
    completed: "bg-slate-200 text-slate-700",
    failed: "bg-rose-100 text-rose-800",
    canceled: "bg-slate-200 text-slate-700",
  };

  return (
    <div className="p-8 max-w-5xl">
      <h1 className="text-2xl font-bold mb-1">Dial</h1>
      <p className="text-slate-500 mb-6">Place a single outbound call</p>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <form onSubmit={placeCall}>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-4 py-3 text-2xl text-center font-mono tracking-wider focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="+91..."
            />
            <div className="grid grid-cols-3 gap-3 mt-5">
              {KEYPAD.flat().map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => press(k)}
                  className="aspect-square bg-slate-50 hover:bg-slate-100 active:bg-slate-200 rounded-full text-2xl font-semibold transition"
                >
                  {k}
                </button>
              ))}
            </div>
            <div className="flex gap-3 mt-5">
              <button
                type="button"
                onClick={backspace}
                className="flex-1 py-3 bg-slate-100 hover:bg-slate-200 rounded-lg font-medium"
              >
                ⌫
              </button>
              <button
                type="submit"
                disabled={calling}
                className="flex-[2] py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white font-semibold rounded-lg transition"
              >
                {calling ? "Placing..." : "📞  Call"}
              </button>
            </div>
            {error && <p className="text-rose-600 mt-3 text-sm">{error}</p>}
            {callSid && (
              <div className="mt-4 text-sm flex items-center gap-2">
                <span
                  className={`px-3 py-1 rounded-full font-medium ${
                    statusColor[callStatus] ?? "bg-slate-200 text-slate-700"
                  }`}
                >
                  {callStatus || "queued"}
                </span>
                <span className="text-slate-500 font-mono text-xs">{callSid}</span>
              </div>
            )}
          </form>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col">
          <div className="px-5 py-3 border-b border-slate-200">
            <h2 className="font-semibold">Live transcript</h2>
          </div>
          <div ref={transcriptRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-1.5 font-mono text-sm min-h-[300px] max-h-[500px]">
            {turns.length === 0 ? (
              <p className="text-slate-400">(no conversation yet)</p>
            ) : (
              turns.map((t, i) => (
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
      </div>
    </div>
  );
}
