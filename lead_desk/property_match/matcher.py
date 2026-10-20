"""Filter + rank listings for a scored buyer lead. Scores properties, never people."""

from __future__ import annotations

import math
import unicodedata

from ..schema import Intent, Lead, LeadScore, Listing, ListingMatch, Operation, SearchFilters
from .providers import ListingProvider


def _fold(text: str | None) -> str:
    nfkd = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def filters_for_lead(lead: Lead, score: LeadScore, exclude_ids: list[str] | None = None,
                     budget_tolerance: float = 0.10) -> SearchFilters | None:
    """Translate what the lead asked for into listing filters. None => no matching for this lead."""
    if score.intent == Intent.BUY:
        operation = Operation.BUY
    elif score.intent == Intent.RENT:
        operation = Operation.RENT
    else:
        return None
    prefs = lead.preferences
    return SearchFilters(
        operation=operation,
        concelho=lead.city,
        typologies=[prefs.typology] if prefs.typology else [],
        max_price_eur=int(lead.budget_eur * (1 + budget_tolerance)) if lead.budget_eur else None,
        min_area_m2=prefs.min_area_m2,
        required_amenities=list(prefs.amenities),
        exclude_listing_ids=list(exclude_ids or []),
    )


def passes(listing: Listing, f: SearchFilters) -> bool:
    if listing.operation != f.operation or listing.listing_id in f.exclude_listing_ids:
        return False
    if f.district and _fold(listing.district) != _fold(f.district):
        return False
    if f.concelho and _fold(listing.concelho) != _fold(f.concelho):
        return False
    if f.freguesia and _fold(listing.freguesia) != _fold(f.freguesia):
        return False
    if f.radius_km is not None and f.center_lat is not None and f.center_lon is not None:
        if listing.lat is None or listing.lon is None:
            return False
        if haversine_km(f.center_lat, f.center_lon, listing.lat, listing.lon) > f.radius_km:
            return False
    if f.typologies and listing.typology not in f.typologies:
        return False
    if f.min_rooms is not None and listing.rooms < f.min_rooms:
        return False
    if f.max_rooms is not None and listing.rooms > f.max_rooms:
        return False
    if f.min_price_eur is not None and listing.price_eur < f.min_price_eur:
        return False
    if f.max_price_eur is not None and listing.price_eur > f.max_price_eur:
        return False
    if f.max_condo_fee_eur is not None and (listing.condo_fee_eur or 0) > f.max_condo_fee_eur:
        return False
    if f.min_area_m2 is not None and listing.area_m2 < f.min_area_m2:
        return False
    if f.max_area_m2 is not None and listing.area_m2 > f.max_area_m2:
        return False
    if f.conditions and listing.condition not in f.conditions:
        return False
    if f.energy_classes and (listing.energy_class or "") not in f.energy_classes:
        return False
    if f.required_amenities and not set(f.required_amenities) <= set(listing.amenities):
        return False
    return True


def rank(listing: Listing, f: SearchFilters, budget_eur: int | None) -> ListingMatch:
    score = 50.0
    reasons: list[str] = []
    if f.concelho:
        reasons.append(f"in {listing.concelho}")
    if f.typologies:
        reasons.append(f"{listing.typology.value} as requested")
    if budget_eur:
        ratio = listing.price_eur / budget_eur
        if ratio <= 1.0:
            score += 30 * (1 - abs(0.92 - ratio))
            reasons.append(f"€{listing.price_eur:,} is within the stated budget")
        else:
            score += 10 * (1 - (ratio - 1) / 0.10)
            reasons.append(f"€{listing.price_eur:,} is up to 10% above the stated budget")
    if f.min_area_m2:
        score += min(10.0, (listing.area_m2 - f.min_area_m2) / 5)
        reasons.append(f"{listing.area_m2} m² (asked ≥ {f.min_area_m2} m²)")
    if f.required_amenities:
        reasons.append("has " + ", ".join(f.required_amenities))
    if listing.energy_class and listing.energy_class[0] in "AB":
        score += 5
        reasons.append(f"energy class {listing.energy_class}")
    return ListingMatch(listing=listing, match_score=round(score, 1), reasons=reasons)


def match_listings(provider: ListingProvider, filters: SearchFilters, budget_eur: int | None,
                   limit: int = 3) -> list[ListingMatch]:
    pool = [l for l in provider.candidates(filters) if passes(l, filters)]
    ranked = sorted((rank(l, filters, budget_eur) for l in pool), key=lambda m: (-m.match_score, m.listing.listing_id))
    return ranked[:limit]
