"""Listing providers behind one interface.

- `IdealistaProvider`: Idealista Search API (v3.5). Used when IDEALISTA_API_KEY / IDEALISTA_API_SECRET are set.
  API access requires Idealista partner approval.
- `MockInventoryProvider`: synthetic `mock_lst_*` listings. Used when Idealista credentials are absent,
  and as the fallback if an Idealista call fails (listings keep `source="mock"` so the agent can tell).
- `ScrapeProvider`: disabled until a ToS / legal review.
"""

from __future__ import annotations

import base64
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Protocol

from ..config import Settings
from ..schema import Listing, Operation, SearchFilters, Typology

MOCK_INVENTORY = Path(__file__).resolve().parents[1] / "data" / "mock_inventory.json"

# Approximate centres used to build Idealista's `center` + `distance` geo query.
CITY_CENTROIDS: dict[str, tuple[float, float]] = {
    "Lisboa": (38.7223, -9.1393), "Porto": (41.1579, -8.6291), "Braga": (41.5454, -8.4265),
    "Cascais": (38.6979, -9.4215), "Faro": (37.0194, -7.9304), "Coimbra": (40.2033, -8.4103),
    "Sintra": (38.8029, -9.3817), "Oeiras": (38.6970, -9.3017), "Almada": (38.6790, -9.1569),
    "Setúbal": (38.5244, -8.8882), "Aveiro": (40.6405, -8.6538), "Matosinhos": (41.1844, -8.6963),
    "Vila Nova de Gaia": (41.1239, -8.6118), "Loulé": (37.1377, -8.0197), "Lagos": (37.1028, -8.6730),
    "Funchal": (32.6669, -16.9241), "Évora": (38.5714, -7.9135), "Leiria": (39.7436, -8.8071),
}

# Our amenity names -> Idealista search flags. The API enforces these, so matches inherit them.
IDEALISTA_AMENITY_FLAGS = {
    "lift": "elevator", "parking": "garage", "terrace": "terrace", "pool": "swimmingPool",
    "air_conditioning": "airConditioning", "storage": "storeRoom",
}
IDEALISTA_CONDITION = {"good": "used", "renew": "to_renovate", "newdevelopment": "new"}


class ProviderError(RuntimeError):
    pass


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


# (method, url, headers, body) -> parsed JSON
HttpFn = Callable[[str, str, dict[str, str], bytes], dict]


def _urllib_http(method: str, url: str, headers: dict[str, str], body: bytes) -> dict:
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read() or b"{}")
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise ProviderError(f"Idealista request failed: {exc}") from exc


class IdealistaProvider:
    """Read-only Idealista Search API client (OAuth2 client credentials + POST /3.5/{country}/search)."""

    name = "idealista"
    TOKEN_URL = "https://api.idealista.com/oauth/token"
    SEARCH_URL = "https://api.idealista.com/3.5/{country}/search"

    def __init__(self, settings: Settings, http: HttpFn | None = None):
        if not settings.idealista_configured:
            raise ProviderError("Idealista credentials missing (IDEALISTA_API_KEY / IDEALISTA_API_SECRET).")
        self.settings = settings
        self.http = http or _urllib_http
        self._token: str | None = None
        self._token_expiry = 0.0

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        s = self.settings
        basic = base64.b64encode(
            f"{urllib.parse.quote(s.idealista_api_key)}:{urllib.parse.quote(s.idealista_api_secret)}".encode()
        ).decode()
        data = self.http("POST", self.TOKEN_URL, {
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        }, urllib.parse.urlencode({"grant_type": "client_credentials", "scope": "read"}).encode())
        if "access_token" not in data:
            raise ProviderError("Idealista token response had no access_token")
        self._token = data["access_token"]
        self._token_expiry = time.time() + float(data.get("expires_in", 3600))
        return self._token

    def search_params(self, filters: SearchFilters) -> dict[str, str] | None:
        """Idealista needs a centre + distance; None when we cannot place the search."""
        s = self.settings
        if filters.center_lat is not None and filters.center_lon is not None:
            lat, lon = filters.center_lat, filters.center_lon
        elif filters.concelho in CITY_CENTROIDS:
            lat, lon = CITY_CENTROIDS[filters.concelho]
        else:
            return None
        radius_km = filters.radius_km or s.idealista_default_radius_km
        params = {
            "country": s.idealista_country,
            "operation": "sale" if filters.operation == Operation.BUY else "rent",
            "propertyType": "homes",
            "center": f"{lat},{lon}",
            "distance": str(int(radius_km * 1000)),
            "maxItems": str(min(s.idealista_max_items, 50)),
            "numPage": "1",
            "locale": "pt",
        }
        if filters.max_price_eur:
            params["maxPrice"] = str(filters.max_price_eur)
        if filters.min_price_eur:
            params["minPrice"] = str(filters.min_price_eur)
        if filters.min_area_m2:
            params["minSize"] = str(filters.min_area_m2)
        if filters.max_area_m2:
            params["maxSize"] = str(filters.max_area_m2)
        if filters.typologies:
            rooms = sorted({4 if t == Typology.T5_PLUS else int(t.value[1]) for t in filters.typologies})
            params["bedrooms"] = ",".join(str(r) for r in rooms)
        for amenity in filters.required_amenities:
            if amenity in IDEALISTA_AMENITY_FLAGS:
                params[IDEALISTA_AMENITY_FLAGS[amenity]] = "true"
        return params

    def to_listing(self, el: dict, filters: SearchFilters) -> Listing:
        rooms = int(el.get("rooms") or 0)
        typology = Typology.T5_PLUS if rooms >= 5 else Typology(f"T{rooms}")
        amenities = {a for a in filters.required_amenities if a in IDEALISTA_AMENITY_FLAGS}
        if el.get("hasLift"):
            amenities.add("lift")
        if (el.get("parkingSpace") or {}).get("hasParkingSpace"):
            amenities.add("parking")
        municipality = el.get("municipality") or filters.concelho or ""
        area = el.get("neighborhood") or el.get("district") or municipality
        return Listing(
            listing_id=f"idealista_{el['propertyCode']}",
            title=f"{typology.value} in {area}, {municipality} (Idealista)",
            operation=filters.operation,
            district=el.get("province") or municipality,
            concelho=municipality,
            freguesia=el.get("district"),
            lat=el.get("latitude"),
            lon=el.get("longitude"),
            typology=typology,
            rooms=rooms,
            area_m2=int(el.get("size") or 0),
            price_eur=int(el.get("price") or 0),
            condition=IDEALISTA_CONDITION.get(el.get("status", ""), "used"),
            amenities=sorted(amenities),
            source="idealista",
        )

    def candidates(self, filters: SearchFilters) -> list[Listing]:
        params = self.search_params(filters)
        if params is None:
            return []
        url = self.SEARCH_URL.format(country=self.settings.idealista_country)
        data = self.http("POST", url, {
            "Authorization": f"Bearer {self._access_token()}",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        }, urllib.parse.urlencode(params).encode())
        return [self.to_listing(el, filters) for el in data.get("elementList", []) if el.get("propertyCode")]


class FallbackProvider:
    """Try the primary provider; on failure, warn and use the fallback."""

    def __init__(self, primary: ListingProvider, fallback: ListingProvider, warn: Callable[[str], None] | None = None):
        self.primary, self.fallback = primary, fallback
        self.name = f"{primary.name}+{fallback.name}"
        self.warn = warn or (lambda msg: print(msg, file=sys.stderr))

    def candidates(self, filters: SearchFilters) -> list[Listing]:
        try:
            return self.primary.candidates(filters)
        except ProviderError as exc:
            self.warn(f"[listings] {self.primary.name} unavailable ({exc}); using {self.fallback.name} inventory")
            return self.fallback.candidates(filters)


class ScrapeProvider:
    """Public-page extraction. Disabled until ToS / legal review; not part of Round 1/2."""

    name = "scrape"

    def __init__(self, settings: Settings):
        if not settings.feature_scrape_listings:
            raise RuntimeError("Listing scraping is disabled (FEATURE_SCRAPE_LISTINGS=false).")

    def candidates(self, filters: SearchFilters) -> list[Listing]:
        raise NotImplementedError("Scraping requires a documented ToS/legal review before it is built.")


def get_provider(settings: Settings, http: HttpFn | None = None) -> ListingProvider:
    if settings.feature_scrape_listings:
        return ScrapeProvider(settings)
    if settings.idealista_configured:
        return FallbackProvider(IdealistaProvider(settings, http=http), MockInventoryProvider())
    return MockInventoryProvider()
