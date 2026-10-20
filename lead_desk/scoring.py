"""Deterministic HOT / WARM / COLD classifier with a plain-language rationale.

Port of `src/scoring_engine.py::score_lead_rules` (seed `rules-v1`) plus the band gates written in
`n8n/prompts/lead_scoring_v1.md` that the seed code does not enforce:

  HOT requires buy/sell intent AND (timeline <= 90 days OR views >= 8 OR saved >= 3) AND contactable.

`strict_policy=False` reproduces the seed `rules-v1` output exactly (used for parity tests).
An LLM may later be used for *drafts only*; the band always comes from these rules.
"""

from __future__ import annotations

from .guardrail import check_fields
from .schema import Band, Intent, Lead, LeadScore

SELL_HITS = ("vender", "venda", "avaliar", "valuation", "sell my", "quero vender")
BUY_HITS = ("comprar", "compra", "compre", "buy", "proposta", "visita", "mortgage", "crédito habitação")
RENT_HITS = ("arrendar", "arrendamento", "rent", "aluguer", "alugar")
# rules-v1.1 only: phrasings present in data/synthetic_leads.csv that the seed lists miss.
SELL_HITS_V11 = ("selling", "listar o", "listar a", "pôr à venda", "por à venda", "colocar à venda")
BUY_HITS_V11 = ("buying", "purchase")
BROWSING_HITS = ("só a ver", "just looking", "curiosidade", "maybe later", "sem pressa")
SPAM_HITS = ("crypto", "seo backlink", "guaranteed profit")
REMOTE_HITS = ("from abroad", "abroad", "relocating", "relocate", "vivo fora", "moro fora", "no estrangeiro")

NEXT_ACTIONS = {
    "rent_parked": "Route to lettings only if the branch runs that book. Sales agents should not rush-call.",
    "cold_drip": "Park in a low-frequency drip. Do not phone. Review in 30 days if they return.",
    "hot_call": "Agent calls within 60 minutes and offers a viewing or listing appointment.",
    "hot_no_phone": "Agent emails/WhatsApp in 2 hours asking for a phone number and a viewing window.",
    "warm_needs_phone": "Agent replies today asking for a phone number and a viewing window; upgrade to HOT once contactable.",
    "warm_qualify": "Send a short qualifying question (budget or timing) then book a call this week.",
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


def logistics_notes(lead: Lead) -> list[str]:
    """Operational hints for the agent. Never fed into the score."""
    text = lead.message.lower()
    notes: list[str] = []
    if any(k in text for k in REMOTE_HITS):
        notes.append("Lead may not be local right now: offer a video viewing or flexible viewing slots.")
    if lead.portal_listing_ref:
        notes.append(f"Enquiry references portal listing {lead.portal_listing_ref}.")
    return notes


def score_lead(lead: Lead, *, strict_policy: bool = True, sales_led: bool = True) -> LeadScore:
    intent = detect_intent(lead.message, extended=strict_policy)
    text = lead.message.lower()
    browsing = any(p in text for p in BROWSING_HITS)
    spam = any(p in text for p in SPAM_HITS)
    contactable = lead.phone_provided or lead.replied_to_agent
    strong_activity = lead.property_views_7d >= 8 or lead.saved_listings >= 3
    near_timeline = lead.timeline_days is not None and lead.timeline_days <= 90

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

    if strong_activity:
        points += 12
        reasons.append("recent search behaviour shows active comparison")
    elif lead.property_views_7d >= 3:
        points += 6
        reasons.append("some recent listing views")

    if contactable:
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

    if intent == Intent.RENT and not spam and sales_led:
        band, action = Band.COLD, "rent_parked"
    elif spam or points < 35:
        band, action = Band.COLD, "cold_drip"
    elif hot_candidate and not strict_policy:
        band, action = Band.HOT, ("hot_call" if contactable else "hot_no_phone")
    elif hot_candidate and contactable and (near_timeline or strong_activity):
        band, action = Band.HOT, "hot_call"
    elif hot_candidate and not contactable:
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
        model_version="rules-v1.1" if strict_policy else "rules-v1",
    )
