import type { Band, Channel, Intent, PacketStatus } from "../types";

const eur = new Intl.NumberFormat("pt-PT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });

export function formatEur(value: number | null | undefined, perMonth = false): string {
  if (value == null) return "—";
  return eur.format(value) + (perMonth ? "/mês" : "");
}

export function formatTimeline(days: number | null | undefined): string {
  if (days == null) return "Not stated";
  if (days <= 1) return "Within a day";
  if (days <= 14) return `${days} days`;
  if (days <= 90) return `~${Math.round(days / 7)} weeks`;
  if (days <= 365) return `~${Math.round(days / 30)} months`;
  return "Over a year";
}

export function timeAgo(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return "—";
  const seconds = Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return `${Math.round(hours / 24)} d ago`;
}

export const BAND_LABEL: Record<Band, string> = { HOT: "Hot", WARM: "Warm", COLD: "Cold" };

export const STATUS_LABEL: Record<PacketStatus, string> = {
  pending_review: "Needs review",
  approved: "Approved",
  rejected: "Rejected",
  blocked_guardrail: "Blocked",
};

export const INTENT_LABEL: Record<Intent, string> = {
  buy: "Buyer",
  sell: "Seller",
  rent: "Renter",
  unknown: "Unclear",
};

export const CHANNEL_LABEL: Record<Channel, string> = { email: "Email", telegram: "Telegram" };

export const AMENITY_LABEL: Record<string, string> = {
  parking: "Parking",
  balcony: "Balcony",
  terrace: "Terrace",
  lift: "Lift",
  pool: "Pool",
  garden: "Garden",
  air_conditioning: "A/C",
  storage: "Storage",
};

/**
 * The engine writes "Score uses only operational signals (...). a; b; c. Numeric score=72."
 * Split it into the individual reasons for display.
 */
export function rationaleReasons(rationale: string): string[] {
  const body = rationale.replace(/^Score uses only operational signals \([^)]*\)\.\s*/, "");
  return body
    .replace(/\.?\s*Numeric score=\d+\.?\s*$/, "")
    .split(";")
    .map((r) => r.trim())
    .filter(Boolean)
    .map((r) => r.charAt(0).toUpperCase() + r.slice(1));
}
