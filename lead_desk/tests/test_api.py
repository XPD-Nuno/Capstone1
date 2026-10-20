from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lead_desk.api import create_app


@pytest.fixture
def client(settings) -> TestClient:
    return TestClient(create_app(settings, seed_demo=True, serve_web=False))


def lead(client: TestClient, lead_id: str) -> dict:
    res = client.get(f"/api/leads/{lead_id}")
    assert res.status_code == 200
    return res.json()


def test_stats_reflect_seeded_demo(client):
    stats = client.get("/api/stats").json()
    assert stats["total"] == 7
    assert stats["by_band"] == {"HOT": 3, "WARM": 1, "COLD": 3}
    assert stats["listings_provider"] == "mock"
    assert stats["pending"] + stats["by_status"]["blocked_guardrail"] <= 7


def test_priority_sort_puts_pending_hot_first(client):
    rows = client.get("/api/leads").json()
    assert len(rows) == 7
    assert rows[0]["band"] == "HOT" and rows[0]["status"] == "pending_review"
    bands = [r["band"] for r in rows if r["status"] == "pending_review"]
    assert bands == sorted(bands, key=["HOT", "WARM", "COLD"].index)


def test_filters_and_search(client):
    hot = client.get("/api/leads", params={"band": "HOT"}).json()
    assert {r["band"] for r in hot} == {"HOT"}
    multi = client.get("/api/leads", params=[("band", "HOT"), ("band", "WARM")]).json()
    assert len(multi) == 4
    telegram = client.get("/api/leads", params={"channel": "telegram"}).json()
    assert telegram and {r["channel"] for r in telegram} == {"telegram"}
    assert [r["lead_id"] for r in client.get("/api/leads", params={"q": "lead_9007"}).json()] == ["lead_9007"]
    assert client.get("/api/leads", params={"q": "no-such-term-xyz"}).json() == []


def test_rental_lead_is_warm_with_rental_matches(client):
    detail = lead(client, "lead_9007")
    assert detail["packet"]["score"]["band"] == "WARM"
    assert detail["packet"]["matches"]
    assert all(m["listing"]["operation"] == "rent" for m in detail["packet"]["matches"])


def test_unknown_lead_and_packet_404(client):
    assert client.get("/api/leads/lead_0000").status_code == 404
    assert client.post("/api/packets/pkt_missing/approve").status_code == 404


def test_approve_then_reapprove_conflicts(client):
    packet_id = lead(client, "lead_9001")["packet"]["packet_id"]
    res = client.post(f"/api/packets/{packet_id}/approve", json={"agent_id": "agent_ana", "note": "call today"})
    assert res.status_code == 200
    body = res.json()
    assert body["packet"]["status"] == "approved"
    assert body["decided_by"] == "agent_ana"
    assert any(e["event_type"] == "decision" for e in body["events"])
    assert client.post(f"/api/packets/{packet_id}/approve").status_code == 409
    assert client.post(f"/api/packets/{packet_id}/reject").status_code == 409


def test_reject_whole_packet(client):
    packet_id = lead(client, "lead_9002")["packet"]["packet_id"]
    res = client.post(f"/api/packets/{packet_id}/reject", json={"agent_id": "agent_rui"})
    assert res.status_code == 200
    assert res.json()["packet"]["status"] == "rejected"


def test_reject_listing_rematches_without_it(client):
    before = lead(client, "lead_9001")
    old_packet = before["packet"]
    excluded = old_packet["matches"][0]["listing"]["listing_id"]
    res = client.post(f"/api/packets/{old_packet['packet_id']}/reject",
                      json={"agent_id": "agent_ana", "listing_ids": [excluded]})
    assert res.status_code == 200
    after = res.json()
    assert after["packet"]["packet_id"] != old_packet["packet_id"]
    assert after["packet"]["status"] == "pending_review"
    assert excluded in after["rejected_listing_ids"]
    assert excluded not in [m["listing"]["listing_id"] for m in after["packet"]["matches"]]
    assert [p["status"] for p in after["packets"]] == ["pending_review", "rejected"]
    assert client.get("/api/stats").json()["total"] == 7


def test_reject_unknown_listing_conflicts(client):
    packet_id = lead(client, "lead_9001")["packet"]["packet_id"]
    res = client.post(f"/api/packets/{packet_id}/reject", json={"listing_ids": ["mock_lst_999"]})
    assert res.status_code == 409


def test_intake_telegram_and_bad_payload(client):
    update = {"update_id": 1, "message": {"message_id": 5, "date": 1760000000,
                                          "chat": {"id": 424242, "type": "private"},
                                          "text": "Quero comprar T2 em Lisboa até 400000€ nos próximos 2 meses"}}
    res = client.post("/api/intake/telegram", json={"payload": update, "lead_id": "lead_9100"})
    assert res.status_code == 201
    created = res.json()["created"]
    assert [c["lead_id"] for c in created] == ["lead_9100"]
    assert client.get("/api/stats").json()["total"] == 8
    assert client.post("/api/intake/telegram", json={"payload": {"update_id": 2}}).json()["created"] == []
    empty = {"from": "lead_9101@example.invalid", "subject": "", "body": "   "}
    assert client.post("/api/intake/email", json={"payload": empty}).status_code == 422


def test_demo_load_is_idempotent(client):
    assert client.post("/api/demo/load").json()["created"] == []
    assert client.get("/api/stats").json()["total"] == 7
