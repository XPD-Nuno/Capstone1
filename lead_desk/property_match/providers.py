"""Listing providers. v1 ships a mock inventory; partner API and scraping are gated off."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from ..config import Settings
from ..schema import Listing, SearchFilters

MOCK_INVENTORY = Path(__file__).resolve().parents[1] / "data" / "mock_inventory.json"


class ListingProvider(Protocol):
    name: str

    def candidates(self, filters: SearchFilters) -> list[Listing]:
        """Return a candidate pool. Fine-grained filtering + ranking happens in `matcher`."""


class MockInventoryProvider:
    name = "mock"

    def __init__(self, path: Path = MOCK_INVENTORY):
        with path.open(encoding="utf-8") as handle:
            self._listings = [Listing(**row) for row in json.load(handle)]

    def candidates(self, filters: SearchFilters) -> list[Listing]:
        return [l for l in self._listings if l.operation == filters.operation]


class PartnerApiProvider:
    """Placeholder for Idealista / Imovirtual / Casa Sapo partner feeds (needs a partner contract)."""

    name = "partner_api"

    def __init__(self, settings: Settings):
        if not settings.feature_partner_api:
            raise RuntimeError("Partner listings API is disabled (FEATURE_PARTNER_LISTINGS_API=false).")

    def candidates(self, filters: SearchFilters) -> list[Listing]:
        raise NotImplementedError("Partner API integration is planned for Phase D.")


class ScrapeProvider:
    """Public-page extraction. Disabled until ToS / legal review; not part of Round 1/2."""

    name = "scrape"

    def __init__(self, settings: Settings):
        if not settings.feature_scrape_listings:
            raise RuntimeError("Listing scraping is disabled (FEATURE_SCRAPE_LISTINGS=false).")

    def candidates(self, filters: SearchFilters) -> list[Listing]:
        raise NotImplementedError("Scraping requires a documented ToS/legal review before it is built.")


def get_provider(settings: Settings) -> ListingProvider:
    if settings.feature_partner_api:
        return PartnerApiProvider(settings)
    if settings.feature_scrape_listings:
        return ScrapeProvider(settings)
    return MockInventoryProvider()
