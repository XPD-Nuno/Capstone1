from __future__ import annotations

import pytest

from lead_desk.config import Settings
from lead_desk.property_match.matcher import filters_for_lead, match_listings, passes
from lead_desk.property_match.providers import MockInventoryProvider, PartnerApiProvider, ScrapeProvider, get_provider
from lead_desk.schema import Channel, Lead, Operation, SearchFilters, SearchPreferences, Typology
from lead_desk.scoring import score_lead


@pytest.fixture
def provider():
    return MockInventoryProvider()


def test_filters_geo_typology_price_area_amenities(provider):
    f = SearchFilters(concelho="lisboa", typologies=[Typology.T2], max_price_eur=400_000,
                      min_area_m2=80, required_amenities=["lift"])
    ids = [m.listing.listing_id for m in match_listings(provider, f, 380_000, limit=10)]
    assert ids == ["mock_lst_002", "mock_lst_001"] or ids == ["mock_lst_001", "mock_lst_002"]
    for m in match_listings(provider, f, 380_000, limit=10):
        l = m.listing
        assert l.concelho == "Lisboa" and l.typology == Typology.T2 and l.price_eur <= 400_000
        assert l.area_m2 >= 80 and "lift" in l.amenities


def test_exclude_rejected_ids(provider):
    f = SearchFilters(concelho="Lisboa", typologies=[Typology.T2], exclude_listing_ids=["mock_lst_001"])
    assert "mock_lst_001" not in [m.listing.listing_id for m in match_listings(provider, f, None, limit=10)]


def test_radius_condition_energy_condo(provider):
    f = SearchFilters(center_lat=41.15, center_lon=-8.61, radius_km=5)
    concelhos = {m.listing.concelho for m in match_listings(provider, f, None, limit=50)}
    assert concelhos <= {"Porto", "Vila Nova de Gaia"} and concelhos
    f = SearchFilters(energy_classes=["A"], conditions=["new"], max_condo_fee_eur=60)
    assert {m.listing.listing_id for m in match_listings(provider, f, None, limit=50)} == {"mock_lst_013", "mock_lst_015"}


def test_rooms_and_operation(provider):
    f = SearchFilters(operation=Operation.RENT, min_rooms=2)
    assert [m.listing.listing_id for m in match_listings(provider, f, None)] == ["mock_lst_023"]
    listing = provider.candidates(SearchFilters())[0]
    assert not passes(listing, SearchFilters(max_rooms=listing.rooms - 1))


def test_budget_tolerance_and_ranking(provider):
    lead = Lead(lead_id="lead_pm", channel=Channel.EMAIL, message="Quero comprar T2 em Lisboa", city="Lisboa",
                budget_eur=380_000, preferences=SearchPreferences(typology=Typology.T2))
    f = filters_for_lead(lead, score_lead(lead))
    assert f.max_price_eur == 418_000 and f.concelho == "Lisboa"
    matches = match_listings(provider, f, lead.budget_eur, limit=3)
    assert matches[0].listing.price_eur <= 380_000
    assert all(m.reasons for m in matches)


def test_no_filters_for_sellers_or_unknown():
    lead = Lead(lead_id="lead_s", channel=Channel.EMAIL, message="Quero vender o meu T3")
    assert filters_for_lead(lead, score_lead(lead)) is None


def test_partner_and_scrape_providers_are_gated():
    off = Settings()
    assert isinstance(get_provider(off), MockInventoryProvider)
    with pytest.raises(RuntimeError):
        PartnerApiProvider(off)
    with pytest.raises(RuntimeError):
        ScrapeProvider(off)
    with pytest.raises(NotImplementedError):
        get_provider(Settings(feature_scrape_listings=True)).candidates(SearchFilters())
