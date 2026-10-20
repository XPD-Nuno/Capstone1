from __future__ import annotations

from urllib.parse import parse_qs

import pytest

from lead_desk.config import Settings
from lead_desk.property_match.matcher import filters_for_lead, match_listings, passes
from lead_desk.property_match.providers import (
    FallbackProvider,
    IdealistaProvider,
    MockInventoryProvider,
    ProviderError,
    ScrapeProvider,
    get_provider,
)
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


def test_scrape_provider_is_gated():
    with pytest.raises(RuntimeError):
        ScrapeProvider(Settings())
    with pytest.raises(NotImplementedError):
        get_provider(Settings(feature_scrape_listings=True)).candidates(SearchFilters())


IDEALISTA = Settings(idealista_api_key="key", idealista_api_secret="secret")

IDEALISTA_RESPONSE = {"elementList": [
    {"propertyCode": "33445566", "price": 372000.0, "size": 84.0, "rooms": 2, "province": "Lisboa",
     "municipality": "Lisboa", "district": "Arroios", "neighborhood": "Pena", "latitude": 38.72,
     "longitude": -9.135, "status": "good", "hasLift": True, "parkingSpace": {"hasParkingSpace": False}},
    {"propertyCode": "77889900", "price": 455000.0, "size": 101.0, "rooms": 3, "province": "Lisboa",
     "municipality": "Lisboa", "district": "Alvalade", "status": "newdevelopment", "hasLift": True},
]}


class FakeIdealista:
    def __init__(self, fail_search=False):
        self.calls = []
        self.fail_search = fail_search

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url, headers, parse_qs(body.decode())))
        if url.endswith("/oauth/token"):
            return {"access_token": "tok", "expires_in": 3600}
        if self.fail_search:
            raise ProviderError("HTTP 429")
        return IDEALISTA_RESPONSE


def test_idealista_absent_credentials_fall_back_to_mock():
    assert isinstance(get_provider(Settings()), MockInventoryProvider)
    with pytest.raises(ProviderError):
        IdealistaProvider(Settings())


def test_idealista_search_params_token_and_mapping():
    http = FakeIdealista()
    provider = get_provider(IDEALISTA, http=http)
    assert isinstance(provider, FallbackProvider) and provider.name == "idealista+mock"
    f = SearchFilters(concelho="Lisboa", typologies=[Typology.T2], max_price_eur=418_000, required_amenities=["lift"])
    listings = provider.candidates(f)
    token_call, search_call = http.calls
    assert token_call[2]["Authorization"].startswith("Basic ") and token_call[3]["grant_type"] == ["client_credentials"]
    assert search_call[1] == "https://api.idealista.com/3.5/pt/search"
    assert search_call[2]["Authorization"] == "Bearer tok"
    q = {k: v[0] for k, v in search_call[3].items()}
    assert q["operation"] == "sale" and q["propertyType"] == "homes" and q["center"] == "38.7223,-9.1393"
    assert (q["distance"], q["maxPrice"], q["bedrooms"], q["elevator"]) == ("10000", "418000", "2", "true")
    first = listings[0]
    assert first.listing_id == "idealista_33445566" and first.source == "idealista"
    assert (first.concelho, first.freguesia, first.typology, first.price_eur, first.area_m2) == ("Lisboa", "Arroios", Typology.T2, 372_000, 84)
    assert "lift" in first.amenities and listings[1].condition == "new"
    ranked = match_listings(provider, f, 380_000)
    assert [m.listing.listing_id for m in ranked] == ["idealista_33445566"]
    provider.candidates(f)
    assert len([c for c in http.calls if c[1].endswith("/oauth/token")]) == 1


def test_idealista_needs_a_location_and_rent_operation():
    p = IdealistaProvider(IDEALISTA, http=FakeIdealista())
    assert p.search_params(SearchFilters(concelho="Nowhere")) is None
    assert p.candidates(SearchFilters()) == []
    q = p.search_params(SearchFilters(operation=Operation.RENT, center_lat=41.1, center_lon=-8.6, radius_km=2.5,
                                      typologies=[Typology.T5_PLUS]))
    assert (q["operation"], q["center"], q["distance"], q["bedrooms"]) == ("rent", "41.1,-8.6", "2500", "4")


def test_idealista_error_falls_back_to_mock_with_warning():
    warnings = []
    provider = FallbackProvider(IdealistaProvider(IDEALISTA, http=FakeIdealista(fail_search=True)),
                                MockInventoryProvider(), warn=warnings.append)
    listings = provider.candidates(SearchFilters(concelho="Lisboa"))
    assert listings and all(l.source == "mock" for l in listings)
    assert "idealista unavailable" in warnings[0]
