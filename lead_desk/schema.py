"""Shared Pydantic models for the Lead Desk pipeline.

Every adapter (email / WhatsApp / Telegram / synthetic file) normalizes into `Lead`.
Everything downstream (scoring, matching, packets, notifiers, repository) only sees `Lead`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Channel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"


class Intent(str, Enum):
    BUY = "buy"
    SELL = "sell"
    RENT = "rent"
    UNKNOWN = "unknown"


class Band(str, Enum):
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"


class Operation(str, Enum):
    BUY = "buy"
    RENT = "rent"


class Typology(str, Enum):
    T0 = "T0"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"
    T5_PLUS = "T5+"


class SearchPreferences(BaseModel):
    """What the lead said they are looking for. Property attributes only."""

    typology: Typology | None = None
    min_area_m2: int | None = None
    amenities: list[str] = Field(default_factory=list)


class Lead(BaseModel):
    """Channel-agnostic lead. `lead_id` must be a synthetic `lead_*` id in demos."""

    lead_id: str
    tenant_id: str = "tenant_demo"
    channel: Channel
    source: str = Field(default="direct", description="e.g. idealista, imovirtual, website, direct")
    received_at: datetime = Field(default_factory=utcnow)
    contact_handle: str | None = Field(default=None, description="Sender address / chat id as received; synthetic in demos")
    dedup_key: str | None = None
    portal_listing_ref: str | None = None
    city: str | None = None
    message: str
    budget_eur: int | None = None
    timeline_days: int | None = None
    property_views_7d: int = 0
    saved_listings: int = 0
    replied_to_agent: bool = False
    phone_provided: bool = False
    email_provided: bool = False
    preferences: SearchPreferences = Field(default_factory=SearchPreferences)
    raw_ref: str | None = Field(default=None, description="Pointer to the raw payload (message id), not the payload itself")

    @field_validator("lead_id")
    @classmethod
    def lead_id_prefix(cls, value: str) -> str:
        if not value.startswith("lead_"):
            raise ValueError("lead_id must start with 'lead_' (synthetic ids only)")
        return value

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be empty")
        return value.strip()


class LeadScore(BaseModel):
    lead_id: str
    intent: Intent
    band: Band
    score_0_100: int = Field(ge=0, le=100)
    rationale: str
    next_action: str
    used_banned_attribute: bool = False
    model_version: str = "rules-v1.1"

    @field_validator("rationale")
    @classmethod
    def no_empty_rationale(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("rationale must not be empty")
        return value


class Listing(BaseModel):
    listing_id: str
    title: str
    operation: Operation
    district: str
    concelho: str
    freguesia: str | None = None
    lat: float | None = None
    lon: float | None = None
    typology: Typology
    rooms: int
    area_m2: int
    price_eur: int
    condo_fee_eur: int | None = None
    condition: str = "used"
    energy_class: str | None = None
    amenities: list[str] = Field(default_factory=list)
    source: str = "mock"


class SearchFilters(BaseModel):
    """Idealista-class filters. Applied to listings, never to people."""

    operation: Operation = Operation.BUY
    district: str | None = None
    concelho: str | None = None
    freguesia: str | None = None
    center_lat: float | None = None
    center_lon: float | None = None
    radius_km: float | None = None
    typologies: list[Typology] = Field(default_factory=list)
    min_rooms: int | None = None
    max_rooms: int | None = None
    min_price_eur: int | None = None
    max_price_eur: int | None = None
    max_condo_fee_eur: int | None = None
    min_area_m2: int | None = None
    max_area_m2: int | None = None
    conditions: list[str] = Field(default_factory=list)
    energy_classes: list[str] = Field(default_factory=list)
    required_amenities: list[str] = Field(default_factory=list)
    exclude_listing_ids: list[str] = Field(default_factory=list)


class ListingMatch(BaseModel):
    listing: Listing
    match_score: float
    reasons: list[str]


class GuardrailResult(BaseModel):
    passed: bool
    hits: list[str] = Field(default_factory=list)
    checked_fields: list[str] = Field(default_factory=list)


class PacketStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED_GUARDRAIL = "blocked_guardrail"


class AgentPacket(BaseModel):
    """What the human agent sees. It is addressed to the agent, never to the customer."""

    packet_id: str
    created_at: datetime = Field(default_factory=utcnow)
    audience: str = "agent_only"
    lead: Lead
    score: LeadScore
    logistics_notes: list[str] = Field(default_factory=list)
    filters_used: SearchFilters | None = None
    matches: list[ListingMatch] = Field(default_factory=list)
    draft_reply_for_agent: str = Field(
        description="Draft the agent may copy and send from their own channel. The system never sends it."
    )
    guardrail: GuardrailResult
    status: PacketStatus = PacketStatus.PENDING_REVIEW
    decision_note: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
