"""Banned-attribute guardrail for anything the system writes (rationales, next actions, drafts).

It checks system-generated text only. A customer may mention living abroad or their family;
that is their message, not a scoring signal. What we must never do is *reason* with it.
"""

from __future__ import annotations

import re

from .schema import GuardrailResult

# Seed list from src/scoring_engine.py (BANNED_RATIONALE_TERMS), extended with the remaining
# policy categories (ethnicity, disability, sexual orientation, family status) and the AGENTS.md
# proxies (neighbourhood-as-person-quality, language ability).
BANNED_TERMS: tuple[str, ...] = (
    # seed list
    "nationality", "nacionalidade",
    "race", "raça",
    "gender", "género", "genero",
    "religion", "religião", "religiao",
    "immigrant", "imigrante",
    "foreigner quality",
    "poor neighbourhood", "bairro pobre",
    "gypsy", "cigano",
    # policy categories not in the seed list
    "ethnicity", "ethnic", "etnia", "étnico", "etnico",
    "disability", "disabled", "deficiência", "deficiencia",
    "sexual orientation", "orientação sexual", "orientacao sexual",
    "family status", "marital status", "estado civil",
    "pregnant", "grávida", "gravida",
    # neighbourhood as a quality-of-person proxy
    "bad neighbourhood", "bad neighborhood", "rough neighbourhood", "rough area",
    "bairro mau", "bairro problemático", "bairro problematico", "bairro social",
    # language ability as a proxy
    "language ability", "speaks portuguese", "doesn't speak portuguese", "does not speak portuguese",
    "fala português", "fala portugues", "não fala", "nao fala",
    "foreigner", "estrangeiro", "estrangeira",
)

_PATTERN = re.compile(
    r"(?<![\wÀ-ÿ])(" + "|".join(re.escape(t) for t in sorted(BANNED_TERMS, key=len, reverse=True)) + r")(?![\wÀ-ÿ])",
    re.IGNORECASE,
)


def find_banned_terms(text: str) -> list[str]:
    """Whole-word / whole-phrase matches, so 'terrace' does not trip 'race'."""
    return sorted({m.group(1).lower() for m in _PATTERN.finditer(text or "")})


def check_fields(fields: dict[str, str]) -> GuardrailResult:
    hits: list[str] = []
    for name, value in fields.items():
        hits.extend(f"{name}:{term}" for term in find_banned_terms(value))
    return GuardrailResult(passed=not hits, hits=hits, checked_fields=sorted(fields))
