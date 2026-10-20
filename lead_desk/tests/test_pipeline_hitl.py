from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from conftest import ROOT
from lead_desk import cli
from lead_desk.config import Settings
from lead_desk.guardrail import check_fields, find_banned_terms
from lead_desk.hitl import review_packet
from lead_desk.intake.webhooks import handle_webhook
from lead_desk.notifiers import (
    CustomerRecipientError,
    EmailNotifier,
    TelegramNotifier,
    WhatsAppNotifier,
    build_notifiers,
    packet_digest,
)
from lead_desk.packet import WITHHELD, build_packet
from lead_desk.pipeline import LeadDesk
from lead_desk.schema import Channel, Lead, PacketStatus
from lead_desk.scoring import score_lead
from lead_desk.storage.repository import LeadRepository

PAYLOADS = json.loads((ROOT / "lead_desk" / "data" / "synthetic_payloads.json").read_text(encoding="utf-8"))


def make_desk(settings: Settings, notify=("cli",), out=None) -> tuple[LeadDesk, list[str]]:
    lines: list[str] = []
    printer = out or lines.append
    return LeadDesk(settings, LeadRepository(":memory:"), build_notifiers(list(notify), settings, out=printer)), lines


def scripted(*answers):
    it = iter(answers)

    def _input(_prompt):
        try:
            return next(it)
        except StopIteration:
            raise EOFError
    return _input


def ingest(desk, idx):
    env = PAYLOADS[idx]
    return desk.ingest(env["channel"], env["payload"], lead_id=env.get("lead_id"), signals=env.get("signals"))


def test_all_synthetic_payloads_expected_bands(settings):
    desk, _ = make_desk(settings)
    bands = {}
    for i in range(len(PAYLOADS)):
        for p in ingest(desk, i):
            bands[p.lead.lead_id] = p.score.band.value
            assert p.status == PacketStatus.PENDING_REVIEW and p.guardrail.passed
            assert p.audience == "agent_only"
    assert bands == {"lead_9001": "HOT", "lead_9002": "HOT", "lead_9003": "WARM", "lead_9004": "COLD",
                     "lead_9005": "COLD", "lead_9006": "HOT", "lead_9007": "COLD"}


def test_approve_records_decision_and_sends_nothing(settings):
    desk, lines = make_desk(settings)
    [packet] = ingest(desk, 0)
    decided = review_packet(desk, packet, input_fn=scripted("a"), out=lines.append)
    assert decided.status == PacketStatus.APPROVED
    assert "Nothing was sent to the customer" in lines[-1]
    events = [e["event_type"] for e in desk.repo.events("lead_9001")]
    assert events[:2] == ["ingested", "scored"] and events[-1] == "decision"
    assert desk.repo.pending_packets() == []


def test_reject_listing_rematches_and_excludes(settings):
    desk, lines = make_desk(settings)
    [packet] = ingest(desk, 0)
    first_ids = [m.listing.listing_id for m in packet.matches]
    assert first_ids
    decided = review_packet(desk, packet, input_fn=scripted(f"r {first_ids[0]}", "a"), out=lines.append)
    assert decided.packet_id != packet.packet_id and decided.status == PacketStatus.APPROVED
    assert first_ids[0] not in [m.listing.listing_id for m in decided.matches]
    assert desk.repo.rejected_listing_ids("lead_9001") == [first_ids[0]]
    [again] = ingest(desk, 0)
    assert first_ids[0] not in [m.listing.listing_id for m in again.matches]


def test_reject_whole_packet_and_skip_and_eof(settings):
    desk, lines = make_desk(settings)
    [p1] = ingest(desk, 2)
    assert review_packet(desk, p1, input_fn=scripted("r"), out=lines.append).status == PacketStatus.REJECTED
    [p2] = ingest(desk, 3)
    assert review_packet(desk, p2, input_fn=scripted("s"), out=lines.append).status == PacketStatus.PENDING_REVIEW
    assert review_packet(desk, p2, input_fn=scripted(), out=lines.append).status == PacketStatus.PENDING_REVIEW
    assert review_packet(desk, p2, input_fn=scripted("r mock_lst_999", "zzz", "s"), out=lines.append).status == PacketStatus.PENDING_REVIEW


def test_repeat_contact_dedups_to_same_lead(settings):
    desk, _ = make_desk(settings)
    a = desk.ingest("telegram", {"update_id": 1, "message": {"chat": {"id": 77}, "from": {"id": 77}, "text": "Quero comprar T2 no Porto"}})
    b = desk.ingest("telegram", {"update_id": 2, "message": {"chat": {"id": 77}, "from": {"id": 77}, "text": "Orçamento 300 mil"}})
    assert a[0].lead.lead_id == b[0].lead.lead_id
    assert len(desk.repo.list_leads()) == 1


def test_guardrail_blocks_packet_and_approval(settings):
    assert find_banned_terms("Rooftop terrace with a view") == []
    assert find_banned_terms("lower priority because of nationality") == ["nationality"]
    assert find_banned_terms("Não fala português") == ["não fala"]
    lead = Lead(lead_id="lead_g", channel=Channel.EMAIL, message="Quero comprar T2 em Lisboa")
    score = score_lead(lead).model_copy(update={"rationale": "Downgraded: bad neighbourhood"})
    packet = build_packet(lead, score, notes=[], filters=None, matches=[])
    assert packet.status == PacketStatus.BLOCKED_GUARDRAIL
    assert packet.draft_reply_for_agent == WITHHELD
    assert packet.guardrail.hits == ["rationale:bad neighbourhood"]
    desk, lines = make_desk(settings)
    desk.repo.upsert_lead(lead)
    desk.repo.save_packet(packet)
    out = review_packet(desk, packet, input_fn=scripted("a", "r"), out=lines.append)
    assert out.status == PacketStatus.REJECTED
    assert any("Cannot approve" in l for l in lines)
    assert check_fields({"draft": "Olá, obrigado"}).passed


def test_same_packet_json_through_all_notifier_stubs_dry_run(settings):
    desk, lines = make_desk(settings, notify=("cli", "email", "whatsapp", "telegram"))
    [packet] = ingest(desk, 5)
    digest = packet_digest(packet)
    notified = [e["payload"] for e in desk.repo.events("lead_9006") if e["event_type"] == "notified"]
    assert [n["channel"] for n in notified] == ["cli", "email", "whatsapp", "telegram"]
    assert {n["packet_sha256"] for n in notified} == {digest}
    assert [n["dry_run"] for n in notified] == [False, True, True, True]
    previews = [l for l in lines if l.startswith("--- [dry-run:")]
    assert len(previews) == 3 and all(digest[:16] in p for p in previews)
    assert "[attachment" in previews[0]


def test_notifiers_dry_run_when_configured_but_not_live():
    s = Settings(telegram_bot_token="x", agent_telegram_chat_id="123", notify_live=False)
    n = TelegramNotifier(s, out=lambda _: None)
    assert n.configured and not n.live


def test_notifier_refuses_customer_as_recipient(settings):
    desk, _ = make_desk(settings)
    [packet] = ingest(desk, 1)
    s = Settings(agent_whatsapp_to=packet.lead.contact_handle)
    with pytest.raises(CustomerRecipientError):
        WhatsAppNotifier(s, out=lambda _: None).notify(packet)
    [packet] = ingest(desk, 0)
    with pytest.raises(CustomerRecipientError):
        EmailNotifier(Settings(agent_email_to="LEAD_9001@example.invalid"), out=lambda _: None).notify(packet)


def test_whatsapp_webhook_verify_signature_and_ingest():
    s = Settings(whatsapp_verify_token="vt", whatsapp_app_secret="sec")
    desk, _ = make_desk(s)
    assert handle_webhook(desk, "GET", "/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=vt&hub.challenge=42", {}, b"") == (200, "42")
    assert handle_webhook(desk, "GET", "/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=no&hub.challenge=42", {}, b"")[0] == 403
    body = json.dumps(PAYLOADS[1]["payload"]).encode()
    assert handle_webhook(desk, "POST", "/webhooks/whatsapp", {"X-Hub-Signature-256": "sha256=bad"}, body)[0] == 401
    sig = "sha256=" + hmac.new(b"sec", body, hashlib.sha256).hexdigest()
    status, resp = handle_webhook(desk, "POST", "/webhooks/whatsapp", {"X-Hub-Signature-256": sig}, body)
    assert status == 200 and resp["packets"][0]["band"] == "HOT"
    assert len(desk.repo.pending_packets()) == 1


def test_telegram_webhook_secret_and_junk():
    desk, _ = make_desk(Settings(telegram_webhook_secret="tg"))
    body = json.dumps(PAYLOADS[3]["payload"]).encode()
    assert handle_webhook(desk, "POST", "/webhooks/telegram", {}, body)[0] == 401
    status, resp = handle_webhook(desk, "POST", "/webhooks/telegram", {"X-Telegram-Bot-Api-Secret-Token": "tg"}, body)
    assert status == 200 and resp["packets"][0]["band"] == "COLD"
    assert handle_webhook(desk, "POST", "/webhooks/telegram", {"X-Telegram-Bot-Api-Secret-Token": "tg"}, b"not json")[1].get("ignored")
    assert handle_webhook(desk, "GET", "/nope", {}, b"")[0] == 404


def test_cli_demo_and_imap_poll_and_review(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", scripted("a", "r", "s"))
    assert cli.main(["demo", "--notify", "all", "--json"]) == 0
    out = capsys.readouterr().out
    assert "APPROVED by agent_demo" in out and "[dry-run:telegram]" in out and '"audience": "agent_only"' in out
    db = str(tmp_path / "desk.sqlite3")
    assert cli.main(["imap-poll", "--db", db]) == 0
    monkeypatch.setattr("builtins.input", scripted("a", "a"))
    assert cli.main(["review", "--db", db]) == 0
    assert "2 packet(s) pending review" in capsys.readouterr().out
    assert LeadRepository(db).pending_packets() == []
