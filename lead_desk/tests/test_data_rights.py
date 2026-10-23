from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lead_desk.api import create_app
from lead_desk.cli import main
from lead_desk.config import Settings
from lead_desk.pipeline import LeadDesk
from lead_desk.storage.repository import LeadRepository

DEMO = json.loads((Path(__file__).resolve().parents[1] / "data" / "synthetic_payloads.json").read_text(encoding="utf-8"))


def seeded_desk(settings: Settings, db: str = ":memory:") -> LeadDesk:
    desk = LeadDesk(settings, LeadRepository(db, tenant_id=settings.tenant_id), notifiers=[])
    for env in DEMO:
        desk.ingest(env["channel"], env["payload"], lead_id=env.get("lead_id"), signals=env.get("signals"))
    return desk


def backdate(repo: LeadRepository, lead_id: str, days: int) -> None:
    old = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    repo.conn.execute("UPDATE leads SET last_seen_at = ? WHERE lead_id = ?", (old, lead_id))
    repo.conn.execute("UPDATE lead_events SET created_at = ? WHERE lead_id = ?", (old, lead_id))
    repo.conn.commit()


def rows_for(repo: LeadRepository, lead_id: str) -> dict[str, int]:
    return {t: repo.conn.execute(f"SELECT COUNT(*) FROM {t} WHERE lead_id = ?", (lead_id,)).fetchone()[0]
            for t in ("leads", "packets", "lead_events", "rejected_listings")}


def test_export_contains_lead_packets_decisions_and_events(settings):
    desk = seeded_desk(settings)
    packet = desk.repo.packets_for_lead("lead_9001")[0][0]
    desk.rematch_after_rejection(packet, [packet.matches[0].listing.listing_id], "agent_ana")
    data = desk.repo.export_lead("lead_9001")
    assert data["lead"]["lead_id"] == "lead_9001"
    assert data["lead"]["message"]
    assert len(data["packets"]) == 2
    assert data["packets"][0]["status"] == "rejected" and data["packets"][0]["decided_by"] == "agent_ana"
    assert [r["listing_id"] for r in data["rejected_listings"]] == [packet.matches[0].listing.listing_id]
    assert {"ingested", "scored", "packet", "decision", "listing_rejected"} <= {e["event_type"] for e in data["events"]}
    json.dumps(data)
    assert desk.repo.export_lead("lead_0000") is None


def test_delete_erases_everything_and_keeps_only_a_hashed_log(settings):
    desk = seeded_desk(settings)
    packet = desk.repo.packets_for_lead("lead_9001")[0][0]
    desk.rematch_after_rejection(packet, [packet.matches[0].listing.listing_id], "agent_ana")
    counts = desk.repo.delete_lead("lead_9001", actor="agent:agent_ana")
    assert counts["leads"] == 1 and counts["packets"] == 2 and counts["rejected_listings"] == 1
    assert rows_for(desk.repo, "lead_9001") == {"leads": 0, "packets": 0, "lead_events": 0, "rejected_listings": 0}
    assert len(desk.repo.latest_packets()) == len(DEMO) - 1
    log = desk.repo.conn.execute("SELECT * FROM erasure_log").fetchall()
    assert len(log) == 1 and "lead_9001" not in json.dumps([dict(r) for r in log])
    assert desk.repo.erasure_record("lead_9001")["actor"] == "agent:agent_ana"
    assert desk.repo.delete_lead("lead_9001", actor="agent:x") is None


def test_deleted_message_text_is_not_left_in_the_database_file(tmp_path, settings):
    db = tmp_path / "desk.sqlite3"
    desk = seeded_desk(settings, str(db))
    assert desk.repo.conn.execute("PRAGMA secure_delete").fetchone()[0] == 1
    marker = "T3 with garden in Cascais".encode()
    assert marker in db.read_bytes()
    desk.repo.delete_lead("lead_9006", actor="agent:a")
    desk.repo.close()
    assert marker not in db.read_bytes()


def test_deleted_contact_comes_back_as_a_fresh_lead(settings):
    desk = seeded_desk(settings)
    env = next(e for e in DEMO if e["lead_id"] == "lead_9002")
    desk.repo.delete_lead("lead_9002", actor="agent:a")
    desk.ingest(env["channel"], env["payload"], lead_id=env["lead_id"], signals=env.get("signals"))
    data = desk.repo.export_lead("lead_9002")
    assert len(data["packets"]) == 1 and data["rejected_listings"] == []


def test_purge_only_erases_inactive_leads(settings):
    desk = seeded_desk(settings)
    backdate(desk.repo, "lead_9004", 400)
    backdate(desk.repo, "lead_9005", 200)
    assert desk.repo.purge_inactive(365, dry_run=True) == ["lead_9004"]
    assert rows_for(desk.repo, "lead_9004")["leads"] == 1
    assert desk.repo.purge_inactive(180) == ["lead_9004", "lead_9005"]
    assert len(desk.repo.latest_packets()) == len(DEMO) - 2
    assert desk.repo.erasure_record("lead_9004")["reason"] == "retention"
    future = datetime.now(timezone.utc) + timedelta(days=31)
    assert len(desk.repo.purge_inactive(30, now=future)) == len(DEMO) - 2
    with pytest.raises(ValueError):
        desk.repo.purge_inactive(0)


def test_recent_decision_counts_as_activity(settings):
    desk = seeded_desk(settings)
    backdate(desk.repo, "lead_9001", 400)
    desk.repo.add_event("lead_9001", "decision", {"status": "approved"}, actor="agent:a")
    desk.repo.conn.commit()
    assert "lead_9001" not in desk.repo.purge_inactive(365, dry_run=True)


@pytest.fixture
def client(settings) -> TestClient:
    return TestClient(create_app(settings, seed_demo=True, serve_web=False))


def test_api_export_delete_and_purge(client):
    res = client.get("/api/leads/lead_9003/export")
    assert res.status_code == 200
    assert res.headers["content-disposition"] == 'attachment; filename="lead_9003.json"'
    assert res.json()["lead"]["lead_id"] == "lead_9003"
    assert client.get("/api/leads/lead_0000/export").status_code == 404

    res = client.delete("/api/leads/lead_9003", params={"agent_id": "agent_rui"})
    assert res.status_code == 200 and res.json()["deleted"]["leads"] == 1
    assert client.get("/api/leads/lead_9003").status_code == 404
    assert client.delete("/api/leads/lead_9003").status_code == 404
    assert client.get("/api/stats").json()["total"] == len(DEMO) - 1

    assert client.post("/api/retention/purge").status_code == 422
    res = client.post("/api/retention/purge", params={"days": 30, "dry_run": True})
    assert res.json() == {"days": 30, "dry_run": True, "lead_ids": []}


def test_api_purge_uses_configured_retention():
    desk = seeded_desk(Settings(db_path=":memory:", retention_days=90))
    backdate(desk.repo, "lead_9007", 120)
    client = TestClient(create_app(desk.settings, desk=desk, serve_web=False))
    assert client.post("/api/retention/purge").json()["lead_ids"] == ["lead_9007"]
    assert client.get("/api/stats").json()["total"] == len(DEMO) - 1


def test_cli_export_delete_and_purge(tmp_path, capsys, settings):
    db = str(tmp_path / "desk.sqlite3")
    seeded_desk(settings, db).repo.close()
    out = tmp_path / "lead_9006.json"
    assert main(["export-lead", "lead_9006", "--db", db, "--out", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["lead"]["lead_id"] == "lead_9006"

    assert main(["delete-lead", "lead_9006", "--db", db, "--yes", "--agent", "agent_ana"]) == 0
    assert "Erased lead_9006" in capsys.readouterr().out
    assert main(["export-lead", "lead_9006", "--db", db]) == 1

    repo = LeadRepository(db)
    backdate(repo, "lead_9004", 400)
    repo.close()
    assert main(["purge", "--db", db, "--days", "365", "--dry-run"]) == 0
    assert "Would erase 1 lead(s)" in capsys.readouterr().out
    assert main(["purge", "--db", db, "--days", "365"]) == 0
    assert LeadRepository(db).export_lead("lead_9004") is None


def test_cli_delete_asks_for_confirmation(tmp_path, monkeypatch, settings):
    db = str(tmp_path / "desk.sqlite3")
    seeded_desk(settings, db).repo.close()
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    assert main(["delete-lead", "lead_9005", "--db", db]) == 1
    assert LeadRepository(db).export_lead("lead_9005") is not None


def test_cli_purge_without_retention_fails(tmp_path, monkeypatch):
    monkeypatch.delenv("LEAD_DESK_RETENTION_DAYS", raising=False)
    assert main(["--env-file", str(tmp_path / "none.env"), "purge", "--db", str(tmp_path / "x.sqlite3")]) == 2
