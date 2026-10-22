"""SQLite repository. Plain SQL with `?` placeholders kept close to what Postgres needs."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..schema import AgentPacket, Lead, LeadScore, PacketStatus

SCHEMA = Path(__file__).with_name("schema_sqlite.sql")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LeadRepository:
    def __init__(self, db_path: str | Path = ":memory:", tenant_id: str = "tenant_demo"):
        self.tenant_id = tenant_id
        # Callers that share the repository across threads (webhook server) must serialize access.
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Deleted rows are overwritten with zeros instead of lingering in free pages.
        self.conn.execute("PRAGMA secure_delete = ON")
        self.conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        self.conn.execute(
            "INSERT OR IGNORE INTO tenants(tenant_id, name, created_at) VALUES (?, ?, ?)",
            (tenant_id, "Demo agency (synthetic)", _now()),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------ leads

    def upsert_lead(self, lead: Lead) -> Lead:
        """Dedup on (tenant, dedup_key): a repeat contact keeps its original lead_id."""
        if lead.dedup_key:
            row = self.conn.execute(
                "SELECT lead_id FROM leads WHERE tenant_id = ? AND dedup_key = ?",
                (self.tenant_id, lead.dedup_key),
            ).fetchone()
            if row and row["lead_id"] != lead.lead_id:
                lead = lead.model_copy(update={"lead_id": row["lead_id"]})
        now = _now()
        self.conn.execute(
            """
            INSERT INTO leads(lead_id, tenant_id, channel, source, dedup_key, contact_handle,
                              portal_listing_ref, city, first_seen_at, last_seen_at, lead_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(lead_id) DO UPDATE SET
                last_seen_at = excluded.last_seen_at,
                lead_json = excluded.lead_json,
                city = COALESCE(excluded.city, leads.city),
                portal_listing_ref = COALESCE(excluded.portal_listing_ref, leads.portal_listing_ref)
            """,
            (lead.lead_id, self.tenant_id, lead.channel.value, lead.source, lead.dedup_key,
             lead.contact_handle, lead.portal_listing_ref, lead.city, now, now, lead.model_dump_json()),
        )
        self.add_event(lead.lead_id, "ingested", {"channel": lead.channel.value, "raw_ref": lead.raw_ref})
        self.conn.commit()
        return lead

    def record_score(self, score: LeadScore) -> None:
        self.conn.execute(
            "UPDATE leads SET latest_band = ?, latest_score = ? WHERE lead_id = ?",
            (score.band.value, score.score_0_100, score.lead_id),
        )
        self.add_event(score.lead_id, "scored", score.model_dump(mode="json"))
        self.conn.commit()

    def get_lead(self, lead_id: str) -> Lead | None:
        row = self.conn.execute("SELECT lead_json FROM leads WHERE lead_id = ?", (lead_id,)).fetchone()
        return Lead.model_validate_json(row["lead_json"]) if row else None

    def list_leads(self, band: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT lead_id, channel, source, city, latest_band, latest_score, last_seen_at FROM leads WHERE tenant_id = ?"
        args: list[Any] = [self.tenant_id]
        if band:
            sql += " AND latest_band = ?"
            args.append(band)
        return [dict(r) for r in self.conn.execute(sql + " ORDER BY last_seen_at DESC", args)]

    # ------------------------------------------------------------ events

    def add_event(self, lead_id: str, event_type: str, payload: dict[str, Any], actor: str = "system") -> None:
        self.conn.execute(
            "INSERT INTO lead_events(tenant_id, lead_id, event_type, actor, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (self.tenant_id, lead_id, event_type, actor, json.dumps(payload, ensure_ascii=False, default=str), _now()),
        )

    def events(self, lead_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT event_type, actor, payload_json, created_at FROM lead_events WHERE lead_id = ? ORDER BY event_id",
            (lead_id,),
        )
        return [dict(r) | {"payload": json.loads(r["payload_json"])} for r in rows]

    # ------------------------------------------------------------ packets + HITL

    def save_packet(self, packet: AgentPacket) -> None:
        self.conn.execute(
            """
            INSERT INTO packets(packet_id, tenant_id, lead_id, status, packet_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(packet_id) DO UPDATE SET status = excluded.status, packet_json = excluded.packet_json
            """,
            (packet.packet_id, self.tenant_id, packet.lead.lead_id, packet.status.value,
             packet.model_dump_json(), packet.created_at.isoformat()),
        )
        self.add_event(packet.lead.lead_id, "packet", {"packet_id": packet.packet_id, "status": packet.status.value,
                                                       "listing_ids": [m.listing.listing_id for m in packet.matches]})
        self.conn.commit()

    def pending_packets(self) -> list[AgentPacket]:
        rows = self.conn.execute(
            "SELECT packet_json FROM packets WHERE tenant_id = ? AND status = ? ORDER BY created_at",
            (self.tenant_id, PacketStatus.PENDING_REVIEW.value),
        )
        return [AgentPacket.model_validate_json(r["packet_json"]) for r in rows]

    def get_packet(self, packet_id: str) -> tuple[AgentPacket, dict[str, Any]] | None:
        """Packet plus its decision metadata (`decided_at`, `decided_by`)."""
        row = self.conn.execute(
            "SELECT packet_json, decided_at, decided_by FROM packets WHERE tenant_id = ? AND packet_id = ?",
            (self.tenant_id, packet_id),
        ).fetchone()
        if not row:
            return None
        return AgentPacket.model_validate_json(row["packet_json"]), {"decided_at": row["decided_at"], "decided_by": row["decided_by"]}

    def packets_for_lead(self, lead_id: str) -> list[tuple[AgentPacket, dict[str, Any]]]:
        rows = self.conn.execute(
            "SELECT packet_json, decided_at, decided_by FROM packets WHERE tenant_id = ? AND lead_id = ? ORDER BY created_at DESC",
            (self.tenant_id, lead_id),
        )
        return [(AgentPacket.model_validate_json(r["packet_json"]), {"decided_at": r["decided_at"], "decided_by": r["decided_by"]})
                for r in rows]

    def latest_packets(self) -> list[tuple[AgentPacket, dict[str, Any]]]:
        """The current packet for every lead: what the review queue shows."""
        rows = self.conn.execute(
            """
            SELECT p.packet_json, p.decided_at, p.decided_by FROM packets p
            WHERE p.tenant_id = ? AND p.created_at = (
                SELECT MAX(p2.created_at) FROM packets p2 WHERE p2.tenant_id = p.tenant_id AND p2.lead_id = p.lead_id
            )
            ORDER BY p.created_at DESC
            """,
            (self.tenant_id,),
        )
        return [(AgentPacket.model_validate_json(r["packet_json"]), {"decided_at": r["decided_at"], "decided_by": r["decided_by"]})
                for r in rows]

    def record_decision(self, packet: AgentPacket, status: PacketStatus, agent_id: str, note: str | None = None) -> AgentPacket:
        decided = packet.model_copy(update={"status": status, "decision_note": note})
        self.conn.execute(
            "UPDATE packets SET status = ?, packet_json = ?, decided_at = ?, decided_by = ? WHERE packet_id = ?",
            (status.value, decided.model_dump_json(), _now(), agent_id, packet.packet_id),
        )
        self.add_event(packet.lead.lead_id, "decision",
                       {"packet_id": packet.packet_id, "status": status.value, "note": note}, actor=f"agent:{agent_id}")
        self.conn.commit()
        return decided

    def reject_listings(self, lead_id: str, listing_ids: list[str], agent_id: str) -> None:
        for listing_id in listing_ids:
            self.conn.execute(
                "INSERT OR IGNORE INTO rejected_listings(tenant_id, lead_id, listing_id, rejected_by, created_at) VALUES (?, ?, ?, ?, ?)",
                (self.tenant_id, lead_id, listing_id, agent_id, _now()),
            )
        self.add_event(lead_id, "listing_rejected", {"listing_ids": listing_ids}, actor=f"agent:{agent_id}")
        self.conn.commit()

    def rejected_listing_ids(self, lead_id: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT listing_id FROM rejected_listings WHERE tenant_id = ? AND lead_id = ? ORDER BY listing_id",
            (self.tenant_id, lead_id),
        )
        return [r["listing_id"] for r in rows]

    # ------------------------------------------------------------ data-subject requests + retention

    def export_lead(self, lead_id: str) -> dict[str, Any] | None:
        """Everything stored about one lead, as plain JSON-ready data."""
        row = self.conn.execute(
            "SELECT * FROM leads WHERE tenant_id = ? AND lead_id = ?", (self.tenant_id, lead_id)
        ).fetchone()
        if not row:
            return None
        record = {k: row[k] for k in row.keys() if k != "lead_json"}
        packets = self.conn.execute(
            "SELECT packet_id, status, created_at, decided_at, decided_by, packet_json FROM packets "
            "WHERE tenant_id = ? AND lead_id = ? ORDER BY created_at",
            (self.tenant_id, lead_id),
        )
        rejected = self.conn.execute(
            "SELECT listing_id, rejected_by, created_at FROM rejected_listings WHERE tenant_id = ? AND lead_id = ? "
            "ORDER BY listing_id",
            (self.tenant_id, lead_id),
        )
        return {
            "exported_at": _now(),
            "tenant_id": self.tenant_id,
            "lead_id": lead_id,
            "record": record,
            "lead": json.loads(row["lead_json"]),
            "packets": [{k: p[k] for k in p.keys() if k != "packet_json"} | {"packet": json.loads(p["packet_json"])}
                        for p in packets],
            "rejected_listings": [dict(r) for r in rejected],
            "events": [{k: v for k, v in e.items() if k != "payload_json"} for e in self.events(lead_id)],
        }

    def delete_lead(self, lead_id: str, *, actor: str, reason: str = "request") -> dict[str, int] | None:
        """Erase a lead with its packets, decisions, events and listing exclusions. None if unknown."""
        if not self.conn.execute(
            "SELECT 1 FROM leads WHERE tenant_id = ? AND lead_id = ?", (self.tenant_id, lead_id)
        ).fetchone():
            return None
        counts: dict[str, int] = {}
        with self.conn:
            for table in ("lead_events", "packets", "rejected_listings", "leads"):
                cur = self.conn.execute(f"DELETE FROM {table} WHERE tenant_id = ? AND lead_id = ?",
                                        (self.tenant_id, lead_id))
                counts[table] = cur.rowcount
            self.conn.execute(
                "INSERT INTO erasure_log(tenant_id, lead_id_sha256, reason, actor, counts_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (self.tenant_id, hashlib.sha256(lead_id.encode()).hexdigest(), reason, actor,
                 json.dumps(counts), _now()),
            )
        return counts

    def erasure_record(self, lead_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT reason, actor, counts_json, created_at FROM erasure_log WHERE tenant_id = ? AND lead_id_sha256 = ? "
            "ORDER BY erasure_id DESC LIMIT 1",
            (self.tenant_id, hashlib.sha256(lead_id.encode()).hexdigest()),
        ).fetchone()
        return dict(row) | {"counts": json.loads(row["counts_json"])} if row else None

    def leads_inactive_since(self, cutoff: datetime) -> list[str]:
        """Leads whose last activity (contact, scoring, packet or decision) is older than `cutoff`."""
        rows = self.conn.execute(
            """
            SELECT l.lead_id FROM leads l
            WHERE l.tenant_id = ? AND MAX(
                l.last_seen_at,
                COALESCE((SELECT MAX(e.created_at) FROM lead_events e WHERE e.lead_id = l.lead_id), l.last_seen_at)
            ) < ?
            ORDER BY l.lead_id
            """,
            (self.tenant_id, cutoff.astimezone(timezone.utc).isoformat()),
        )
        return [r["lead_id"] for r in rows]

    def purge_inactive(self, days: int, *, now: datetime | None = None, dry_run: bool = False) -> list[str]:
        if days < 1:
            raise ValueError("retention must be at least 1 day")
        cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=days)
        lead_ids = self.leads_inactive_since(cutoff)
        if not dry_run:
            for lead_id in lead_ids:
                self.delete_lead(lead_id, actor="system:retention", reason="retention")
        return lead_ids

    def bump_usage(self, meter: str, quantity: int = 1) -> None:
        period = datetime.now(timezone.utc).strftime("%Y-%m")
        self.conn.execute(
            """
            INSERT INTO usage_meters(tenant_id, period, meter, quantity) VALUES (?, ?, ?, ?)
            ON CONFLICT(tenant_id, period, meter) DO UPDATE SET quantity = usage_meters.quantity + excluded.quantity
            """,
            (self.tenant_id, period, meter, quantity),
        )
        self.conn.commit()
