import type { LeadDetail, LeadFilters, LeadSummary, Stats } from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function leadsQuery(filters: LeadFilters): string {
  const params = new URLSearchParams();
  if (filters.q.trim()) params.set("q", filters.q.trim());
  filters.bands.forEach((b) => params.append("band", b));
  if (filters.status) params.set("status", filters.status);
  if (filters.channel) params.set("channel", filters.channel);
  params.set("sort", filters.sort);
  return params.toString();
}

export const api = {
  stats: () => request<Stats>("/api/stats"),
  leads: (filters: LeadFilters) => request<LeadSummary[]>(`/api/leads?${leadsQuery(filters)}`),
  lead: (leadId: string) => request<LeadDetail>(`/api/leads/${encodeURIComponent(leadId)}`),
  approve: (packetId: string, agentId: string, note?: string) =>
    request<LeadDetail>(`/api/packets/${packetId}/approve`, {
      method: "POST",
      body: JSON.stringify({ agent_id: agentId, note: note || null }),
    }),
  reject: (packetId: string, agentId: string, listingIds: string[] = [], note?: string) =>
    request<LeadDetail>(`/api/packets/${packetId}/reject`, {
      method: "POST",
      body: JSON.stringify({ agent_id: agentId, listing_ids: listingIds, note: note || null }),
    }),
  loadDemo: () => request<{ created: LeadSummary[] }>("/api/demo/load", { method: "POST" }),
};
