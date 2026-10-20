export type Band = "HOT" | "WARM" | "COLD";
export type Channel = "email" | "telegram";
export type PacketStatus = "pending_review" | "approved" | "rejected" | "blocked_guardrail";
export type Intent = "buy" | "sell" | "rent" | "unknown";
export type SortKey = "priority" | "newest" | "score";

export interface LeadSummary {
  lead_id: string;
  packet_id: string;
  channel: Channel;
  source: string;
  city: string | null;
  intent: Intent;
  band: Band;
  score: number;
  status: PacketStatus;
  budget_eur: number | null;
  timeline_days: number | null;
  message_preview: string;
  next_action: string;
  match_count: number;
  received_at: string;
  packet_created_at: string;
  decided_at: string | null;
  decided_by: string | null;
}

export interface Lead {
  lead_id: string;
  channel: Channel;
  source: string;
  received_at: string;
  portal_listing_ref: string | null;
  city: string | null;
  message: string;
  budget_eur: number | null;
  timeline_days: number | null;
  property_views_7d: number;
  saved_listings: number;
  replied_to_agent: boolean;
  phone_provided: boolean;
  email_provided: boolean;
  preferences: { typology: string | null; min_area_m2: number | null; amenities: string[] };
}

export interface LeadScore {
  intent: Intent;
  band: Band;
  score_0_100: number;
  rationale: string;
  next_action: string;
  used_banned_attribute: boolean;
  model_version: string;
}

export interface Listing {
  listing_id: string;
  title: string;
  operation: "buy" | "rent";
  district: string;
  concelho: string;
  freguesia: string | null;
  typology: string;
  rooms: number;
  area_m2: number;
  price_eur: number;
  condo_fee_eur: number | null;
  condition: string;
  energy_class: string | null;
  amenities: string[];
  source: string;
}

export interface ListingMatch {
  listing: Listing;
  match_score: number;
  reasons: string[];
}

export interface AgentPacket {
  packet_id: string;
  created_at: string;
  lead: Lead;
  score: LeadScore;
  logistics_notes: string[];
  matches: ListingMatch[];
  draft_reply_for_agent: string;
  guardrail: { passed: boolean; hits: string[] };
  status: PacketStatus;
  decision_note: string | null;
}

export interface PacketHistoryItem {
  packet_id: string;
  status: PacketStatus;
  created_at: string;
  decided_at: string | null;
  decided_by: string | null;
  decision_note: string | null;
  listing_ids: string[];
}

export interface LeadEvent {
  event_type: string;
  actor: string;
  created_at: string;
  payload: Record<string, unknown>;
}

export interface LeadDetail {
  packet: AgentPacket;
  decided_at: string | null;
  decided_by: string | null;
  rejected_listing_ids: string[];
  packets: PacketHistoryItem[];
  events: LeadEvent[];
}

export interface Stats {
  total: number;
  pending: number;
  by_band: Record<Band, number>;
  by_status: Record<PacketStatus, number>;
  listings_provider: string;
}

export interface LeadFilters {
  q: string;
  bands: Band[];
  status: PacketStatus | "";
  channel: Channel | "";
  sort: SortKey;
}
