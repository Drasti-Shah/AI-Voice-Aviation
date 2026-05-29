export const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8080";

export type Turn = { role: "user" | "bot" | "system"; text: string; ts: number };
export type CallMeta = {
  sid: string;
  to?: string;
  from?: string;
  status?: string;
  created?: number;
  started?: number | null;
  ended?: number | null;
  duration?: number;
  campaign_id?: string | null;
  turn_count?: number;
  user_turns?: number;
  bot_turns?: number;
};
export type Campaign = {
  id: string;
  name: string;
  created: number;
  numbers: string[];
  calls: { to: string; sid: string | null; status: string; meta?: CallMeta }[];
  status: "queued" | "running" | "paused" | "completed";
  cursor: number;
};
export type DashboardData = {
  total_calls: number;
  active_calls: number;
  completed_calls: number;
  avg_duration_s: number;
  active_call_sid: string | null;
  campaigns_count: number;
};

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, init);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export const api = {
  dashboard: () => j<DashboardData>("/api/dashboard"),
  transcript: () => j<{ turns: Turn[] }>("/api/transcript"),
  resetTranscript: () => j<{ ok: boolean }>("/api/transcript/reset", { method: "POST" }),
  call: (to: string) =>
    j<{ sid: string; status: string }>("/api/call", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ to }),
    }),
  callStatus: (sid: string) => j<any>(`/api/call/${sid}`),
  calls: () => j<{ calls: CallMeta[] }>("/api/calls"),
  callTranscript: (sid: string) =>
    j<{ sid: string; meta: CallMeta; metrics: any; turns: Turn[] }>(`/api/calls/${sid}/transcript`),
  recordingUrl: (sid: string) => `${API}/api/calls/${sid}/recording`,
  campaigns: () => j<{ campaigns: Campaign[] }>("/api/campaigns"),
  campaign: (id: string) => j<Campaign>(`/api/campaigns/${id}`),
  createCampaign: (name: string, numbers: string[]) =>
    j<Campaign>("/api/campaigns", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, numbers }),
    }),
  uploadCsv: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch(`${API}/api/campaigns/upload`, { method: "POST", body: fd });
    if (!r.ok) throw new Error(await r.text());
    return r.json() as Promise<{ numbers: string[]; count: number; name: string }>;
  },
  pauseCampaign: (id: string) =>
    j<Campaign>(`/api/campaigns/${id}/pause`, { method: "POST" }),
  resumeCampaign: (id: string) =>
    j<Campaign>(`/api/campaigns/${id}/resume`, { method: "POST" }),
};

export function fmtTime(ts?: number | null): string {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString();
}

export function fmtAgo(ts?: number | null): string {
  if (!ts) return "—";
  const s = Math.floor(Date.now() / 1000 - ts);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}
