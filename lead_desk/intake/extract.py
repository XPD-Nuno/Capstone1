"""Free-text field extraction shared by every intake adapter (PT + EN)."""

from __future__ import annotations

import re
import unicodedata

from ..schema import SearchPreferences, Typology

CITIES = {
    "lisboa": "Lisboa", "lisbon": "Lisboa",
    "porto": "Porto", "oporto": "Porto",
    "braga": "Braga", "cascais": "Cascais", "faro": "Faro", "coimbra": "Coimbra",
    "sintra": "Sintra", "oeiras": "Oeiras", "almada": "Almada", "setubal": "Setúbal",
    "aveiro": "Aveiro", "matosinhos": "Matosinhos", "vila nova de gaia": "Vila Nova de Gaia",
    "gaia": "Vila Nova de Gaia", "loule": "Loulé", "lagos": "Lagos", "funchal": "Funchal",
    "evora": "Évora", "leiria": "Leiria",
}

AMENITIES = {
    "parking": ("garagem", "estacionamento", "parking", "garage", "lugar de garagem"),
    "balcony": ("varanda", "balcony"),
    "terrace": ("terraço", "terraco", "terrace"),
    "lift": ("elevador", "lift", "elevator"),
    "pool": ("piscina", "pool"),
    "garden": ("jardim", "garden"),
    "air_conditioning": ("ar condicionado", "air conditioning", "a/c"),
    "storage": ("arrecadação", "arrecadacao", "storage"),
}

_NUM = r"(\d+(?:[.,]\d+)?)"


def _fold(text: str) -> str:
    """Lowercase and strip accents for keyword matching."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _to_float(raw: str) -> float:
    return float(raw.replace(",", "."))


def extract_budget_eur(text: str) -> int | None:
    t = text.lower()
    candidates: list[int] = []
    for m in re.finditer(_NUM + r"\s*(milhões|milhoes|milhão|milhao|million|mn)\b", t):
        candidates.append(int(_to_float(m.group(1)) * 1_000_000))
    for m in re.finditer(_NUM + r"\s*(mil|k)\b", t):
        candidates.append(int(_to_float(m.group(1)) * 1_000))
    grouped = r"(\d{1,3}(?:[.\s\u00a0]\d{3})+|\d{3,})"
    for m in re.finditer(r"€\s*" + grouped, t):
        candidates.append(int(re.sub(r"\D", "", m.group(1))))
    for m in re.finditer(grouped + r"\s*(?:€|eur\b|euros\b)", t):
        candidates.append(int(re.sub(r"\D", "", m.group(1))))
    candidates = [c for c in candidates if c >= 100]
    return max(candidates) if candidates else None


_TIMELINE_PHRASES: tuple[tuple[str, int], ...] = (
    ("hoje", 1), ("today", 1),
    ("amanha", 1), ("tomorrow", 1),
    ("esta semana", 7), ("this week", 7),
    ("proxima semana", 14), ("next week", 14),
    ("este mes", 30), ("this month", 30),
    ("proximo mes", 60), ("next month", 60),
    ("este ano", 180), ("this year", 180),
    ("proximo ano", 365), ("next year", 365),
)


def extract_timeline_days(text: str) -> int | None:
    """Smallest horizon mentioned. Durations like 'arrendar por 12 meses' are not timelines."""
    t = _fold(text)
    found: list[int] = []
    for phrase, days in _TIMELINE_PHRASES:
        if re.search(r"\b" + phrase + r"\b", t):
            found.append(days)
    lead_in = r"(?:em|dentro de|nos proximos|proximos|within|in|in the next|next)\s+"
    units = {"dia": 1, "dias": 1, "day": 1, "days": 1, "semana": 7, "semanas": 7, "week": 7, "weeks": 7,
             "mes": 30, "meses": 30, "month": 30, "months": 30, "ano": 365, "anos": 365, "year": 365, "years": 365}
    for m in re.finditer(lead_in + r"(\d+)\s+(dias?|days?|semanas?|weeks?|mes(?:es)?|months?|anos?|years?)\b", t):
        found.append(int(m.group(1)) * units[m.group(2)])
    return min(found) if found else None


def extract_city(text: str) -> str | None:
    t = _fold(text)
    for key in sorted(CITIES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(key) + r"\b", t):
            return CITIES[key]
    return None


def extract_typology(text: str) -> Typology | None:
    m = re.search(r"\bT([0-9])(\+)?(?![\w])", text, re.IGNORECASE)
    if m:
        n = int(m.group(1))
        return Typology.T5_PLUS if n >= 5 else Typology(f"T{n}")
    m = re.search(r"\b(\d)\s*(quartos|bedrooms?|assoalhadas)\b", _fold(text))
    if m:
        n = int(m.group(1))
        return Typology.T5_PLUS if n >= 5 else Typology(f"T{n}")
    return None


def extract_min_area_m2(text: str) -> int | None:
    m = re.search(r"(\d{2,4})\s*(m2|m²|metros quadrados|sqm)", text.lower())
    return int(m.group(1)) if m else None


def extract_amenities(text: str) -> list[str]:
    t = _fold(text)
    return sorted(k for k, words in AMENITIES.items() if any(re.search(r"\b" + re.escape(_fold(w)) + r"\b", t) for w in words))


def extract_preferences(text: str) -> SearchPreferences:
    return SearchPreferences(
        typology=extract_typology(text),
        min_area_m2=extract_min_area_m2(text),
        amenities=extract_amenities(text),
    )


_PHONE_LABEL = re.compile(r"^\s*(telefone|telemóvel|telemovel|tel|phone|mobile)\s*[:\-]\s*\S+", re.IGNORECASE | re.MULTILINE)
_PHONE_NUMBER = re.compile(r"(?:\+351[\s.]?)?\b9[1236]\d[\s.]?\d{3}[\s.]?\d{3}\b")


def mentions_phone(text: str) -> bool:
    return bool(_PHONE_LABEL.search(text) or _PHONE_NUMBER.search(text))


_LISTING_REF = (
    re.compile(r"idealista\.pt/imovel/(\d+)", re.IGNORECASE),
    re.compile(r"imovirtual\.com/\S*?ID([A-Za-z0-9]+)", re.IGNORECASE),
    re.compile(r"\b(?:ref(?:er[eê]ncia)?|listing ref)\.?\s*[:#]\s*([A-Za-z0-9-]{4,})", re.IGNORECASE),
)


def extract_listing_ref(text: str) -> str | None:
    for pattern in _LISTING_REF:
        m = pattern.search(text)
        if m:
            return m.group(1)
    return None
