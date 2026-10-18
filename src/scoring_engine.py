"""Deterministic lead scorer shared by charts, eval, Python POC, and the MVP fallback.

The n8n prompt in n8n/prompts/lead_scoring_v1.md encodes the same policy.
Optional LLM path must return the same JSON schema (LeadScore).
"""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

BANNED_RATIONALE_TERMS = (
    "nationality",
    "nacionalidade",
    "race",
    "raça",
    "gender",
    "género",
    "genero",
    "religion",
    "religião",
    "religiao",
    "immigrant",
    "imigrante",
    "foreigner quality",
    "poor neighbourhood",
    "bairro pobre",
    "gypsy",
    "cigano",
)


class Intent(str, Enum):
    BUY = "buy"
    SELL = "sell"
    RENT = "rent"
    UNKNOWN = "unknown"


class Band(str, Enum):
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"


class LeadInput(BaseModel):
    lead_id: str
    channel: str = "website"
    city: str = "Lisboa"
    message: str
    budget_eur: int | None = None
    timeline_days: int | None = None
    property_views_7d: int = 0
    saved_listings: int = 0
    replied_to_agent: bool = False
    phone_provided: bool = False
    email_provided: bool = True


class LeadScore(BaseModel):
    lead_id: str
    intent: Intent
    band: Band
    score_0_100: int = Field(ge=0, le=100)
    rationale: str
    next_action: str
    used_banned_attribute: bool = False
    model_version: str = "rules-v1"

    @field_validator("rationale")
    @classmethod
    def no_empty_rationale(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("rationale must not be empty")
        return value


def detect_intent(message: str) -> Intent:
    text = message.lower()
    sell_hits = ("vender", "venda", "avaliar", "valuation", "sell my", "quero vender")
    buy_hits = ("comprar", "compra", "compre", "buy", "proposta", "visita", "mortgage", "crédito habitação")
    rent_hits = ("arrendar", "arrendamento", "rent", "aluguer", "alugar")
    sell = any(k in text for k in sell_hits)
    buy = any(k in text for k in buy_hits)
    rent = any(k in text for k in rent_hits)
    if sell and not buy:
        return Intent.SELL
    if buy and not sell:
        return Intent.BUY
    if rent and not buy and not sell:
        return Intent.RENT
    if buy or sell:
        return Intent.BUY if buy else Intent.SELL
    return Intent.UNKNOWN


def _mentions_banned(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in BANNED_RATIONALE_TERMS)


def score_lead_rules(lead: LeadInput) -> LeadScore:
    """Transparent, inspectable scoring. This is the Round 1 POC engine."""
    intent = detect_intent(lead.message)
    text = lead.message.lower()
    browsing = any(
        phrase in text
        for phrase in ("só a ver", "just looking", "curiosidade", "maybe later", "sem pressa")
    )
    spam = any(phrase in text for phrase in ("crypto", "seo backlink", "guaranteed profit"))

    points = 10
    reasons: list[str] = []

    if intent in (Intent.BUY, Intent.SELL):
        points += 25
        reasons.append(f"clear {intent.value} intent in the message")
    elif intent == Intent.RENT:
        points += 8
        reasons.append("rent intent is lower value for this sales-led SME")
    else:
        reasons.append("intent is unclear from the message")

    if intent == Intent.SELL:
        points += 12
        reasons.append("seller leads are not penalised for a missing purchase budget")
    elif lead.budget_eur and lead.budget_eur > 0:
        points += 15
        reasons.append("budget is stated")
    else:
        reasons.append("budget is missing")

    if lead.timeline_days is not None:
        if lead.timeline_days <= 90:
            points += 20
            reasons.append("timeline is within 90 days")
        elif lead.timeline_days <= 365:
            points += 10
            reasons.append("timeline is 3–12 months")
        else:
            points += 2
            reasons.append("timeline is beyond 12 months")
    else:
        reasons.append("timeline is missing")

    if lead.property_views_7d >= 8 or lead.saved_listings >= 3:
        points += 12
        reasons.append("recent search behaviour shows active comparison")
    elif lead.property_views_7d >= 3:
        points += 6
        reasons.append("some recent listing views")

    if lead.phone_provided or lead.replied_to_agent:
        points += 10
        reasons.append("lead is contactable or already in a conversation")

    if browsing:
        points -= 20
        reasons.append("message signals browsing rather than a decision")
    if spam:
        points -= 40
        reasons.append("message looks like spam or an irrelevant pitch")

    points = max(0, min(100, points))

    if intent == Intent.RENT and not spam:
        band = Band.COLD
        next_action = "Route to lettings only if the branch runs that book. Sales agents should not rush-call."
    elif spam or points < 35:
        band = Band.COLD
        next_action = "Park in a low-frequency drip. Do not phone. Review in 30 days if they return."
    elif points >= 70 and intent in (Intent.BUY, Intent.SELL) and (lead.phone_provided or lead.replied_to_agent):
        band = Band.HOT
        next_action = "Agent calls within 60 minutes and offers a viewing or listing appointment."
    elif points >= 70 and intent in (Intent.BUY, Intent.SELL):
        band = Band.HOT
        next_action = "Agent emails/WhatsApp in 2 hours asking for a phone number and a viewing window."
    else:
        band = Band.WARM
        next_action = "Send a short qualifying question (budget or timing) then book a call this week."

    rationale = (
        "Score uses only operational signals (intent, budget, timing, search activity, contactability). "
        + "; ".join(reasons)
        + f". Numeric score={points}."
    )
    banned = _mentions_banned(rationale)
    return LeadScore(
        lead_id=lead.lead_id,
        intent=intent,
        band=band,
        score_0_100=points,
        rationale=rationale,
        next_action=next_action,
        used_banned_attribute=banned,
        model_version="rules-v1",
    )


def lead_score_to_dict(score: LeadScore) -> dict[str, Any]:
    payload = score.model_dump()
    payload["intent"] = score.intent.value
    payload["band"] = score.band.value
    return payload


def parse_llm_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    return json.loads(text)
