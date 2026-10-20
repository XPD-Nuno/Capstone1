import type { Band, Channel, LeadFilters, PacketStatus, SortKey } from "../types";

const BANDS: Band[] = ["HOT", "WARM", "COLD"];
const STATUSES: PacketStatus[] = ["pending_review", "approved", "rejected", "blocked_guardrail"];
const CHANNELS: Channel[] = ["email", "telegram"];
const SORTS: SortKey[] = ["priority", "newest", "score"];

export const DEFAULT_FILTERS: LeadFilters = { q: "", bands: [], status: "", channel: "", sort: "priority" };

export function filtersFromParams(params: URLSearchParams): LeadFilters {
  const status = params.get("status") as PacketStatus | null;
  const channel = params.get("channel") as Channel | null;
  const sort = params.get("sort") as SortKey | null;
  return {
    q: params.get("q") ?? "",
    bands: params.getAll("band").filter((b): b is Band => BANDS.includes(b as Band)),
    status: status && STATUSES.includes(status) ? status : "",
    channel: channel && CHANNELS.includes(channel) ? channel : "",
    sort: sort && SORTS.includes(sort) ? sort : "priority",
  };
}

export function filtersToParams(filters: LeadFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  filters.bands.forEach((b) => params.append("band", b));
  if (filters.status) params.set("status", filters.status);
  if (filters.channel) params.set("channel", filters.channel);
  if (filters.sort !== "priority") params.set("sort", filters.sort);
  return params;
}

export function toggleBand(bands: Band[], band: Band): Band[] {
  return bands.includes(band) ? bands.filter((b) => b !== band) : BANDS.filter((b) => b === band || bands.includes(b));
}

export function isFiltered(filters: LeadFilters): boolean {
  return Boolean(filters.q || filters.bands.length || filters.status || filters.channel);
}
