from __future__ import annotations

import json

import pytest

from conftest import ROOT
from lead_desk.intake.extract import (
    extract_amenities,
    extract_budget_eur,
    extract_city,
    extract_min_area_m2,
    extract_timeline_days,
    extract_typology,
    mentions_phone,
)
from lead_desk.intake.imap_poll import read_eml_dir
from lead_desk.intake.normalize import NormalizeError, normalize, parse_email, parse_telegram
from lead_desk.schema import Channel, Typology

PAYLOADS = json.loads((ROOT / "lead_desk" / "data" / "synthetic_payloads.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("text,expected", [
    ("Orçamento 380 mil", 380_000),
    ("budget 720k", 720_000),
    ("até 1,2 milhões", 1_200_000),
    ("Preço máximo €450.000", 450_000),
    ("valor 395 000 €", 395_000),
    ("até 800 € por mês", 800),
    ("até 300 mil euros", 300_000),
    ("Budget ready", None),
    ("T2 com 80 m2", None),
])
def test_extract_budget(text, expected):
    assert extract_budget_eur(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("Posso visitar amanhã à tarde", 1),
    ("avaliação esta semana", 7),
    ("Viewing this month", 30),
    ("Talvez no próximo ano", 365),
    ("quero mudar dentro de 2 meses", 60),
    ("nos próximos 3 meses", 90),
    ("arrendamento para 12 meses", None),
    ("sem data", None),
])
def test_extract_timeline(text, expected):
    assert extract_timeline_days(text) == expected


def test_extract_misc():
    assert extract_city("casa em Vila Nova de Gaia") == "Vila Nova de Gaia"
    assert extract_city("flat in Lisbon") == "Lisboa"
    assert extract_city("Setúbal centro") == "Setúbal"
    assert extract_city("sem cidade") is None
    assert extract_typology("Quero um T3") == Typology.T3
    assert extract_typology("moradia T5+") == Typology.T5_PLUS
    assert extract_typology("2 quartos") == Typology.T2
    assert extract_typology("at 3pm") is None
    assert extract_min_area_m2("pelo menos 90 m²") == 90
    assert extract_amenities("com garagem, varanda e elevador") == ["balcony", "lift", "parking"]
    assert extract_amenities("terraço") == ["terrace"]
    assert mentions_phone("Telefone: [synthetic-redacted]")
    assert not mentions_phone("Telefone:")
    assert not mentions_phone("Quero um T2")


def test_portal_email_raw_rfc822():
    env = PAYLOADS[0]
    lead = parse_email(env["payload"], lead_id=env["lead_id"], signals=env["signals"])
    assert lead.channel == Channel.EMAIL
    assert lead.source == "idealista"
    assert lead.contact_handle == "lead_9001@example.invalid"
    assert lead.message.startswith("Quero comprar T2 em Lisboa")
    assert "Anúncio" not in lead.message
    assert lead.portal_listing_ref == "00000001"
    assert (lead.city, lead.budget_eur, lead.timeline_days) == ("Lisboa", 380_000, 1)
    assert lead.phone_provided and lead.email_provided
    assert lead.preferences.typology == Typology.T2 and lead.preferences.amenities == ["lift"]
    assert lead.property_views_7d == 12


def test_direct_email_dict_includes_subject():
    lead = parse_email({"from": "lead_x@example.invalid", "subject": "Casa em Braga", "body": "Orçamento 250 mil"},
                       lead_id="lead_x")
    assert lead.message.startswith("Casa em Braga")
    assert lead.city == "Braga" and lead.budget_eur == 250_000 and lead.source == "direct_email"
    assert not lead.phone_provided


def test_sample_inbox_eml_files():
    leads = {name: parse_email(raw) for name, raw in read_eml_dir()}
    portal = leads["01_imovirtual_buyer.eml"]
    assert portal.source == "imovirtual" and portal.portal_listing_ref == "IMO-SYN-0001"
    assert portal.preferences.amenities == ["parking"] and portal.timeline_days == 14
    html = leads["02_direct_html_seller.eml"]
    assert "<p>" not in html.message and "vender" in html.message
    assert html.replied_to_agent is True
    assert all(l.lead_id.startswith("lead_") for l in leads.values())


def test_telegram_message_with_phone_line():
    env = PAYLOADS[1]
    lead = parse_telegram(env["payload"], lead_id=env["lead_id"])
    assert lead.channel == Channel.TELEGRAM and lead.phone_provided and not lead.email_provided
    assert lead.city == "Porto" and lead.timeline_days == 7 and lead.raw_ref == "tg:9002"


def test_whatsapp_is_not_an_intake_channel():
    with pytest.raises(ValueError):
        normalize("whatsapp", {"object": "whatsapp_business_account", "entry": []})


def test_telegram_update():
    env = PAYLOADS[3]
    lead = parse_telegram(env["payload"], lead_id=env["lead_id"])
    assert lead.channel == Channel.TELEGRAM and lead.contact_handle == "900009004"
    assert lead.city == "Faro" and not lead.phone_provided
    base = {"update_id": 1, "message": {"chat": {"id": 1}, "from": {"id": 1, "is_bot": False}}}
    assert parse_telegram(base | {"message": base["message"] | {"text": "/start"}}) is None
    assert parse_telegram({"update_id": 2, "message": {"chat": {"id": 1}, "from": {"is_bot": True}, "text": "hi"}}) is None
    assert parse_telegram({"update_id": 3, "my_chat_member": {}}) is None
    replied = parse_telegram(base | {"message": base["message"] | {"text": "Sim, quero visitar", "reply_to_message": {}}})
    assert replied.replied_to_agent


def test_same_contact_gets_same_synthetic_id():
    a = normalize("telegram", {"update_id": 1, "message": {"chat": {"id": 42}, "from": {"id": 42}, "text": "olá T2"}})[0]
    b = normalize("telegram", {"update_id": 2, "message": {"chat": {"id": 42}, "from": {"id": 42}, "text": "outra"}})[0]
    assert a.lead_id == b.lead_id and a.dedup_key == b.dedup_key


def test_empty_email_raises():
    with pytest.raises(NormalizeError):
        parse_email({"from": "lead_y@example.invalid", "subject": "", "body": "   "})
