"""Deterministic HOT / WARM / COLD classifier with a plain-language rationale.

Port of `src/scoring_engine.py::score_lead_rules` (seed `rules-v1`). The default `rules-v1.2` keeps the
seed points table and applies the band policy agreed with the client (docs/project-context, Oct 2026):

  HOT   buy/sell intent, score >= 70, (timeline <= 90 days OR views >= 8 OR saved >= 3),
        and a phone number or a previous reply.
  WARM  real interest that misses the HOT gate, and genuine rental intent (never HOT: lower commission).
  COLD  spam, browsing, unclear intent with a low score, and email-only leads (reachable, but no phone
        number and no previous reply means little to go on).

`strict_policy=False` reproduces the seed `rules-v1` output exactly (used for parity tests).
An LLM may later be used for *drafts only*; the band always comes from these rules.
"""

from __future__ import annotations

from .guardrail import check_fields
from .schema import Band, Intent, Lead, LeadScore

SELL_HITS = ("vender", "venda", "avaliar", "valuation", "sell my", "quero vender")
BUY_HITS = ("comprar", "compra", "compre", "buy", "proposta", "visita", "mortgage", "crédito habitação")
RENT_HITS = ("arrendar", "arrendamento", "rent", "aluguer", "alugar")
# rules-v1.1+ only: phrasings present in data/synthetic_leads.csv that the seed lists miss.
SELL_HITS_V11 = ("selling", "listar o", "listar a", "pôr à venda", "por à venda", "colocar à venda")
BUY_HITS_V11 = ("buying", "purchase")
BROWSING_HITS = ("só a ver", "just looking", "curiosidade", "maybe later", "sem pressa")
SPAM_HITS = ("crypto", "seo backlink", "guaranteed profit")
REMOTE_HITS = ("from abroad", "abroad", "relocating", "relocate", "vivo fora", "moro fora", "no estrangeiro")

MODEL_VERSION = "rules-v1.2"

NEXT_ACTIONS = {
    # seed rules-v1 (kept verbatim for the parity mode)
    "rent_parked": "Route to lettings only if the branch runs that book. Sales agents should not rush-call.",
    "cold_drip": "Park in a low-frequency drip. Do not phone. Review in 30 days if they return.",
    "hot_call": "Agent calls within 60 minutes and offers a viewing or listing appointment.",
    "hot_no_phone": "Agent emails/WhatsApp in 2 hours asking for a phone number and a viewing window.",
    "warm_qualify": "Send a short qualifying question (budget or timing) then book a call this week.",
    # rules-v1.2
    "warm_needs_phone": "Agent replies today asking for a phone number and a viewing window; re-score once they share one.",
    "email_only": "Reply by email with one qualifying question and ask for a phone number. Do not phone. Re-score when they answer.",
    "rent_warm": "Lettings lead: send a short qualifying question (move-in date, budget) and book a call this week, after HOT sales leads.",
}


def detect_intent(message: str, extended: bool = True) -> Intent:
    text = message.lower()
    sell_hits = SELL_HITS + SELL_HITS_V11 if extended else SELL_HITS
    buy_hits = BUY_HITS + BUY_HITS_V11 if extended else BUY_HITS
    sell = any(k in text for k in sell_hits)
    buy = any(k in text for k in buy_hits)
    rent = any(k in text for k in RENT_HITS)
    if sell and not buy:
        return Intent.SELL
    if buy and not sell:
        return Intent.BUY
    if rent and not buy and not sell:
        return Intent.RENT
    if buy or sell:
        return Intent.BUY if buy else Intent.SELL
    return Intent.UNKNOWN


def is_email_only(lead: Lead) -> bool:
    return lead.email_provided and not lead.phone_provided and not lead.replied_to_agent


def logistics_notes(lead: Lead) -> list[str]:
    """Operational hints for the agent. Never fed into the score."""
    text = lead.message.lower()
    notes: list[str] = []
    if any(k in text for k in REMOTE_HITS):
        notes.append("Lead may not be local right now: offer a video viewing or flexible viewing slots.")
    if lead.portal_listing_ref:
        notes.append(f"Enquiry references portal listing {lead.portal_listing_ref}.")
    return notes


def score_lead(lead: Lead, *, strict_policy: bool = True) -> LeadScore:
    intent = detect_intent(lead.message, extended=strict_policy)
    text = lead.message.lower()
    browsing = any(p in text for p in BROWSING_HITS)
    spam = any(p in text for p in SPAM_HITS)
    phone_or_reply = lead.phone_provided or lead.replied_to_agent
    email_only = is_email_only(lead)
    strong_activity = lead.property_views_7d >= 8 or lead.saved_listings >= 3
    near_timeline = lead.timeline_days is not None and lead.timeline_days <= 90

    points = 10
    reasons: list[str] = []

    if intent in (Intent.BUY, Intent.SELL):
        points += 25
        reasons.append(f"clear {intent.value} intent in the message")
    elif intent == Intent.RENT:
        points += 8
        reasons.append("rent intent: lower commission, so capped at WARM" if strict_policy
                       else "rent intent is lower value for this sales-led SME")
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

    if strong_activity:
        points += 12
        reasons.append("recent search behaviour shows active comparison")
    elif lead.property_views_7d >= 3:
        points += 6
        reasons.append("some recent listing views")

    if phone_or_reply:
        points += 10
        reasons.append("lead is contactable or already in a conversation")

    if browsing:
        points -= 20
        reasons.append("message signals browsing rather than a decision")
    if spam:
        points -= 40
        reasons.append("message looks like spam or an irrelevant pitch")

    points = max(0, min(100, points))
    hot_candidate = points >= 70 and intent in (Intent.BUY, Intent.SELL)

    if not strict_policy:
        if intent == Intent.RENT and not spam:
            band, action = Band.COLD, "rent_parked"
        elif spam or points < 35:
            band, action = Band.COLD, "cold_drip"
        elif hot_candidate:
            band, action = Band.HOT, ("hot_call" if phone_or_reply else "hot_no_phone")
        else:
            band, action = Band.WARM, "warm_qualify"
    elif spam or (browsing and points < 35):
        band, action = Band.COLD, "cold_drip"
    elif email_only:
        band, action = Band.COLD, "email_only"
        reasons.append("held at COLD: reachable by email only (no phone number or previous reply yet)")
    elif intent == Intent.RENT:
        band, action = Band.WARM, "rent_warm"
    elif points < 35:
        band, action = Band.COLD, "cold_drip"
    elif hot_candidate and phone_or_reply and (near_timeline or strong_activity):
        band, action = Band.HOT, "hot_call"
    elif hot_candidate and not phone_or_reply:
        band, action = Band.WARM, "warm_needs_phone"
        reasons.append("held at WARM: no phone number or reply yet")
    elif hot_candidate:
        band, action = Band.WARM, "warm_qualify"
        reasons.append("held at WARM: no near-term timeline or strong search activity")
    else:
        band, action = Band.WARM, "warm_qualify"

    rationale = (
        "Score uses only operational signals (intent, budget, timing, search activity, contactability). "
        + "; ".join(reasons)
        + f". Numeric score={points}."
    )
    next_action = NEXT_ACTIONS[action]
    guard = check_fields({"rationale": rationale, "next_action": next_action})
    return LeadScore(
        lead_id=lead.lead_id,
        intent=intent,
        band=band,
        score_0_100=points,
        rationale=rationale,
        next_action=next_action,
        used_banned_attribute=not guard.passed,
        model_version=MODEL_VERSION if strict_policy else "rules-v1",
    )
