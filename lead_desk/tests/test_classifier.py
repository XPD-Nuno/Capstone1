from __future__ import annotations

import csv

import pytest

from conftest import ROOT, eval_case_to_lead
from lead_desk.guardrail import find_banned_terms
from lead_desk.schema import Band, Channel, Intent, Lead
from lead_desk.scoring import detect_intent, is_email_only, logistics_notes, score_lead

# Client decision (Oct 2026): email-only leads are banded COLD. eval_03 has email but no phone and no reply.
V12_OVERRIDES = {"eval_03": "COLD"}


@pytest.mark.parametrize("strict", [True, False])
def test_seed_eval_cases(eval_cases, strict):
    for case in eval_cases:
        score = score_lead(eval_case_to_lead(case), strict_policy=strict)
        expected = V12_OVERRIDES.get(case["lead_id"], case["expected_band"]) if strict else case["expected_band"]
        assert score.band.value == expected, (case["lead_id"], score.score_0_100, score.rationale)
        assert score.intent.value == case["expected_intent"], case["lead_id"]
        assert score.used_banned_attribute is False


def test_abroad_mention_stays_out_of_rationale(eval_cases):
    case = next(c for c in eval_cases if c["lead_id"] == "eval_07")
    lead = eval_case_to_lead(case)
    score = score_lead(lead)
    assert "abroad" not in score.rationale.lower()
    assert find_banned_terms(score.rationale) == []
    assert any("video viewing" in n for n in logistics_notes(lead))


def _csv_lead(row: dict) -> Lead:
    none = lambda v: None if v in ("", None) else int(v)  # noqa: E731
    return Lead(
        lead_id=row["lead_id"], channel=Channel.EMAIL, source=row["channel"], city=row["city"],
        message=row["message"], budget_eur=none(row["budget_eur"]), timeline_days=none(row["timeline_days"]),
        property_views_7d=int(row["property_views_7d"]), saved_listings=int(row["saved_listings"]),
        replied_to_agent=row["replied_to_agent"] == "True", phone_provided=row["phone_provided"] == "True",
        email_provided=row["email_provided"] == "True",
    )


def test_non_strict_mode_is_exact_port_of_round1_engine():
    from src.scoring_engine import LeadInput, score_lead_rules

    with (ROOT / "data" / "synthetic_leads.csv").open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) >= 100
    for row in rows:
        lead = _csv_lead(row)
        ours = score_lead(lead, strict_policy=False)
        theirs = score_lead_rules(LeadInput(**lead.model_dump(include=set(LeadInput.model_fields)) | {"channel": lead.source}))
        assert (ours.band.value, ours.intent.value, ours.score_0_100, ours.next_action) == (
            theirs.band.value, theirs.intent.value, theirs.score_0_100, theirs.next_action), row["lead_id"]


FAMILY_BAND = {"hot_buy": "HOT", "hot_sell": "HOT", "warm": "WARM", "cold": "COLD", "rent": "WARM"}


def test_strict_policy_matches_synthetic_family_labels_after_client_decisions():
    """Family label, except email-only leads are COLD and rentals are WARM (data generator predates both)."""
    with (ROOT / "data" / "synthetic_leads.csv").open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        lead = _csv_lead(row)
        expected = "COLD" if is_email_only(lead) else FAMILY_BAND[row["synthetic_family"]]
        assert score_lead(lead).band.value == expected, (row["lead_id"], row["message"])


def _lead(**kw) -> Lead:
    base = dict(lead_id="lead_t1", channel=Channel.TELEGRAM, message="Quero comprar T2 em Lisboa", budget_eur=300000)
    return Lead(**(base | kw))


def test_hot_requires_contactable():
    lead = _lead(timeline_days=30, property_views_7d=10)
    score = score_lead(lead)
    assert score.score_0_100 >= 70
    assert score.band == Band.WARM
    assert "phone number" in score.next_action
    assert score_lead(lead.model_copy(update={"phone_provided": True})).band == Band.HOT


def test_hot_requires_near_timeline_or_strong_activity():
    lead = _lead(timeline_days=200, property_views_7d=5, phone_provided=True)
    score = score_lead(lead)
    assert score.score_0_100 >= 70 and score.band == Band.WARM
    assert score_lead(lead.model_copy(update={"saved_listings": 3})).band == Band.HOT


def test_genuine_rent_is_warm_never_hot():
    lead = _lead(message="Quero arrendar T1 em Coimbra", budget_eur=800, timeline_days=7, phone_provided=True,
                 property_views_7d=20, saved_listings=9, replied_to_agent=True)
    score = score_lead(lead)
    assert score.band == Band.WARM and "Lettings" in score.next_action
    assert score_lead(_lead(message="Procuro arrendamento em Lisboa", budget_eur=None)).band == Band.WARM
    assert score_lead(_lead(message="Só a ver arrendamentos, sem pressa", budget_eur=None)).band == Band.COLD
    assert score_lead(lead.model_copy(update={"message": "rent crypto guaranteed profit"})).band == Band.COLD


def test_email_only_is_contactable_but_cold():
    lead = _lead(channel=Channel.EMAIL, email_provided=True, timeline_days=14, saved_listings=5)
    assert is_email_only(lead)
    score = score_lead(lead)
    assert score.band == Band.COLD
    assert "email" in score.next_action.lower() and "Do not phone" in score.next_action
    assert "reachable by email only" in score.rationale
    assert score_lead(lead.model_copy(update={"phone_provided": True})).band == Band.HOT
    assert score_lead(lead.model_copy(update={"replied_to_agent": True})).band == Band.HOT


def test_spam_never_hot():
    lead = _lead(message="Buy now crypto guaranteed profit", timeline_days=1, phone_provided=True, saved_listings=9)
    assert score_lead(lead).band == Band.COLD


@pytest.mark.parametrize("text,intent", [
    ("Quero vender a minha casa", Intent.SELL),
    ("Want to buy a flat", Intent.BUY),
    ("Procuro arrendamento", Intent.RENT),
    ("Olá, informação por favor", Intent.UNKNOWN),
    ("Quero vender e comprar", Intent.BUY),
    ("Thinking of selling next month", Intent.SELL),
    ("Herdámos um T2 e queremos listar o mais rápido possível", Intent.SELL),
])
def test_detect_intent(text, intent):
    assert detect_intent(text) == intent


def test_lead_id_must_be_synthetic():
    with pytest.raises(ValueError):
        Lead(lead_id="maria.silva", channel=Channel.EMAIL, message="olá")
