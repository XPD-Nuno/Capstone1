from __future__ import annotations

import json

import pytest

from conftest import ROOT
from lead_desk import cli
from lead_desk.config import Settings
from lead_desk.guardrail import check_fields, find_banned_terms
from lead_desk.hitl import review_packet
from lead_desk.intake.webhooks import handle_webhook
from lead_desk.notifiers import AgentNotifier, CLINotifier, CustomerRecipientError, assert_agent_recipient, packet_digest
from lead_desk.packet import WITHHELD, build_packet
from lead_desk.pipeline import LeadDesk
from lead_desk.schema import Channel, Lead, PacketStatus
from lead_desk.scoring import score_lead
from lead_desk.storage.repository import LeadRepository

PAYLOADS = json.loads((ROOT / "lead_desk" / "data" / "synthetic_payloads.json").read_text(encoding="utf-8"))


def make_desk(settings: Settings, show_json: bool = False) -> tuple[LeadDesk, list[str]]:
    lines: list[str] = []
    notifier = CLINotifier(settings, out=lines.append, show_json=show_json)
    return LeadDesk(settings, LeadRepository(":memory:"), [notifier]), lines


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
    assert bands == {
        "lead_9001": "HOT", "lead_9002": "HOT", "lead_9003": "COLD", "lead_9004": "COLD",
        "lead_9005": "COLD", "lead_9006": "HOT", "lead_9007": "WARM", "lead_9008": "HOT",
        "lead_9009": "WARM", "lead_9010": "WARM", "lead_9011": "WARM", "lead_9012": "WARM",
        "lead_9013": "COLD", "lead_9014": "HOT", "lead_9015": "HOT", "lead_9016": "HOT",
    }


def test_email_only_lead_gets_qualifying_draft_and_rental_gets_rent_matches(settings):
    desk, _ = make_desk(settings)
    [email_only] = ingest(desk, 2)
    assert email_only.score.band.value == "COLD" and email_only.matches == []
    assert "telefone" in email_only.draft_reply_for_agent
    [rent] = ingest(desk, 6)
    assert rent.score.band.value == "WARM"
    assert rent.matches and all(m.listing.operation.value == "rent" for m in rent.matches)


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


def test_cli_desk_is_the_only_delivery_and_prints_packet_json(settings):
    desk, lines = make_desk(settings, show_json=True)
    [packet] = ingest(desk, 5)
    notified = [e["payload"] for e in desk.repo.events("lead_9006") if e["event_type"] == "notified"]
    assert [n["channel"] for n in notified] == ["cli"]
    assert notified[0]["packet_sha256"] == packet_digest(packet)
    assert json.loads(lines[-1])["packet_id"] == packet.packet_id
    assert json.loads(lines[-1])["audience"] == "agent_only"


def test_notifier_interface_kept_for_future_channels(settings):
    class FutureNotifier(AgentNotifier):
        name = "future"

        @property
        def recipient(self):
            return "lead_9001@example.invalid"

    desk, _ = make_desk(settings)
    [packet] = ingest(desk, 0)
    with pytest.raises(NotImplementedError):
        AgentNotifier(settings).notify(packet)
    with pytest.raises(CustomerRecipientError):
        assert_agent_recipient(FutureNotifier(settings).recipient, packet)


def test_no_outbound_notifier_or_whatsapp_code_paths():
    import lead_desk.notifiers as notifiers

    source = (ROOT / "lead_desk" / "notifiers.py").read_text(encoding="utf-8")
    assert "smtplib" not in source and "urllib" not in source
    assert not hasattr(notifiers, "EmailNotifier") and not hasattr(notifiers, "WhatsAppNotifier")
    assert "whatsapp" not in {c.value for c in Channel}


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
    assert cli.main(["demo", "--json"]) == 0
    out = capsys.readouterr().out
    assert "APPROVED by agent_demo" in out and '"audience": "agent_only"' in out
    assert "Listings provider: mock" in out and "dry-run" not in out
    with pytest.raises(SystemExit):
        cli.main(["demo", "--notify", "all"])
    db = str(tmp_path / "desk.sqlite3")
    assert cli.main(["imap-poll", "--db", db]) == 0
    monkeypatch.setattr("builtins.input", scripted("a", "a"))
    assert cli.main(["review", "--db", db]) == 0
    assert "2 packet(s) pending review" in capsys.readouterr().out
    assert LeadRepository(db).pending_packets() == []
