"""FastAPI backend for the Lead Desk web dashboard.

Thin layer over the same pipeline the CLI uses: `LeadDesk` (normalize -> score -> match -> packet)
and `hitl.approve_packet` / `hitl.reject_packet`. The dashboard is a desk the agent reads; nothing
here sends anything to customers or agents.

Demo-grade: no login. Bind to localhost (the default) unless you put it behind an authenticating proxy.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import __version__
from ..config import Settings, load_settings
from ..hitl import DecisionError, approve_packet, reject_packet
from ..intake.normalize import NormalizeError
from ..pipeline import LeadDesk
from ..schema import AgentPacket, Band, Channel, PacketStatus
from ..storage.repository import LeadRepository

DEMO_PAYLOADS = Path(__file__).resolve().parents[1] / "data" / "synthetic_payloads.json"
WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"

BAND_ORDER = {Band.HOT: 0, Band.WARM: 1, Band.COLD: 2}
STATUS_ORDER = {PacketStatus.PENDING_REVIEW: 0, PacketStatus.BLOCKED_GUARDRAIL: 1,
                PacketStatus.APPROVED: 2, PacketStatus.REJECTED: 3}


class LeadSummary(BaseModel):
    lead_id: str
    packet_id: str
    channel: Channel
    source: str
    city: str | None
    intent: str
    band: Band
    score: int
    status: PacketStatus
    budget_eur: int | None
    timeline_days: int | None
    message_preview: str
    next_action: str
    match_count: int
    received_at: datetime
    packet_created_at: datetime
    decided_at: str | None = None
    decided_by: str | None = None


class PacketHistoryItem(BaseModel):
    packet_id: str
    status: PacketStatus
    created_at: datetime
    decided_at: str | None
    decided_by: str | None
    decision_note: str | None
    listing_ids: list[str]


class LeadEvent(BaseModel):
    event_type: str
    actor: str
    created_at: str
    payload: dict[str, Any]


class LeadDetail(BaseModel):
    packet: AgentPacket
    decided_at: str | None = None
    decided_by: str | None = None
    rejected_listing_ids: list[str]
    packets: list[PacketHistoryItem]
    events: list[LeadEvent]


class Stats(BaseModel):
    total: int
    pending: int
    by_band: dict[str, int]
    by_status: dict[str, int]
    listings_provider: str


class ApproveRequest(BaseModel):
    agent_id: str = Field(default="agent_demo", min_length=1, max_length=64)
    note: str | None = Field(default=None, max_length=500)


class RejectRequest(ApproveRequest):
    listing_ids: list[str] = Field(default_factory=list, description="Empty = reject the whole packet")


class IntakeRequest(BaseModel):
    payload: Any = Field(description="Telegram Update object, or an email as raw RFC 822 text / {from, subject, body}")
    lead_id: str | None = None
    signals: dict[str, Any] | None = None


class IntakeResponse(BaseModel):
    created: list[LeadSummary]


def summarize(packet: AgentPacket, meta: dict[str, Any]) -> LeadSummary:
    lead, score = packet.lead, packet.score
    preview = " ".join(lead.message.split())
    return LeadSummary(
        lead_id=lead.lead_id, packet_id=packet.packet_id, channel=lead.channel, source=lead.source,
        city=lead.city, intent=score.intent.value, band=score.band, score=score.score_0_100,
        status=packet.status, budget_eur=lead.budget_eur, timeline_days=lead.timeline_days,
        message_preview=preview[:160] + ("…" if len(preview) > 160 else ""), next_action=score.next_action,
        match_count=len(packet.matches), received_at=lead.received_at, packet_created_at=packet.created_at,
        decided_at=meta.get("decided_at"), decided_by=meta.get("decided_by"),
    )


def matches_query(packet: AgentPacket, q: str) -> bool:
    needle = q.strip().lower()
    if not needle:
        return True
    lead = packet.lead
    haystack = " ".join(filter(None, [
        lead.lead_id, lead.city, lead.source, lead.channel.value, lead.message, packet.score.intent.value,
        lead.preferences.typology.value if lead.preferences.typology else None,
        *[m.listing.listing_id + " " + m.listing.title for m in packet.matches],
    ])).lower()
    return all(term in haystack for term in needle.split())


def create_app(settings: Settings | None = None, *, desk: LeadDesk | None = None, seed_demo: bool = False,
               serve_web: bool = True) -> FastAPI:
    settings = settings or load_settings()
    if desk is None:
        desk = LeadDesk(settings, LeadRepository(settings.db_path, tenant_id=settings.tenant_id), notifiers=[])
    lock = threading.Lock()  # one sqlite connection shared by the threadpool

    app = FastAPI(title="Lead Desk API", version=__version__,
                  description="Score → explain → match → agent decides. Nothing is ever sent to customers.")
    app.state.desk = desk

    def load_demo() -> list[LeadSummary]:
        envelopes = json.loads(DEMO_PAYLOADS.read_text(encoding="utf-8"))
        existing = {p.lead.lead_id for p, _ in desk.repo.latest_packets()}
        created = []
        for env in envelopes:
            if env.get("lead_id") in existing:
                continue
            for packet in desk.ingest(env["channel"], env["payload"], lead_id=env.get("lead_id"), signals=env.get("signals")):
                created.append(summarize(packet, {}))
        return created

    def detail(lead_id: str) -> LeadDetail:
        history = desk.repo.packets_for_lead(lead_id)
        if not history:
            raise HTTPException(404, f"Lead {lead_id} not found")
        packet, meta = history[0]
        return LeadDetail(
            packet=packet, decided_at=meta["decided_at"], decided_by=meta["decided_by"],
            rejected_listing_ids=desk.repo.rejected_listing_ids(lead_id),
            packets=[PacketHistoryItem(packet_id=p.packet_id, status=p.status, created_at=p.created_at,
                                       decided_at=m["decided_at"], decided_by=m["decided_by"],
                                       decision_note=p.decision_note,
                                       listing_ids=[x.listing.listing_id for x in p.matches]) for p, m in history],
            events=[LeadEvent(event_type=e["event_type"], actor=e["actor"], created_at=e["created_at"],
                              payload=e["payload"]) for e in desk.repo.events(lead_id)],
        )

    def packet_or_404(packet_id: str) -> AgentPacket:
        found = desk.repo.get_packet(packet_id)
        if not found:
            raise HTTPException(404, f"Packet {packet_id} not found")
        return found[0]

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "version": __version__, "listings_provider": desk.provider.name}

    @app.get("/api/stats", response_model=Stats)
    def stats() -> Stats:
        with lock:
            packets = [p for p, _ in desk.repo.latest_packets()]
        by_band = {b.value: sum(p.score.band == b for p in packets) for b in Band}
        by_status = {s.value: sum(p.status == s for p in packets) for s in PacketStatus}
        return Stats(total=len(packets), pending=by_status[PacketStatus.PENDING_REVIEW.value], by_band=by_band,
                     by_status=by_status, listings_provider=desk.provider.name)

    @app.get("/api/leads", response_model=list[LeadSummary])
    def list_leads(
        band: list[Band] = Query(default=[]),
        status: list[PacketStatus] = Query(default=[]),
        channel: list[Channel] = Query(default=[]),
        q: str = "",
        sort: Literal["priority", "newest", "score"] = "priority",
    ) -> list[LeadSummary]:
        with lock:
            rows = desk.repo.latest_packets()
        rows = [(p, m) for p, m in rows
                if (not band or p.score.band in band) and (not status or p.status in status)
                and (not channel or p.lead.channel in channel) and matches_query(p, q)]
        if sort == "priority":
            rows.sort(key=lambda r: (STATUS_ORDER[r[0].status], BAND_ORDER[r[0].score.band],
                                     -r[0].score.score_0_100, -r[0].created_at.timestamp()))
        elif sort == "score":
            rows.sort(key=lambda r: -r[0].score.score_0_100)
        else:
            rows.sort(key=lambda r: r[0].created_at, reverse=True)
        return [summarize(p, m) for p, m in rows]

    @app.get("/api/leads/{lead_id}", response_model=LeadDetail)
    def get_lead(lead_id: str) -> LeadDetail:
        with lock:
            return detail(lead_id)

    @app.post("/api/packets/{packet_id}/approve", response_model=LeadDetail)
    def approve(packet_id: str, body: ApproveRequest | None = None) -> LeadDetail:
        body = body or ApproveRequest()
        with lock:
            packet = packet_or_404(packet_id)
            try:
                approve_packet(desk, packet, body.agent_id, note=body.note)
            except DecisionError as exc:
                raise HTTPException(409, str(exc)) from exc
            return detail(packet.lead.lead_id)

    @app.post("/api/packets/{packet_id}/reject", response_model=LeadDetail)
    def reject(packet_id: str, body: RejectRequest | None = None) -> LeadDetail:
        body = body or RejectRequest()
        with lock:
            packet = packet_or_404(packet_id)
            try:
                reject_packet(desk, packet, body.agent_id, listing_ids=body.listing_ids, note=body.note)
            except DecisionError as exc:
                raise HTTPException(409, str(exc)) from exc
            return detail(packet.lead.lead_id)

    @app.post("/api/intake/{channel}", response_model=IntakeResponse, status_code=201)
    def intake(channel: Channel, body: IntakeRequest) -> IntakeResponse:
        with lock:
            try:
                packets = desk.ingest(channel.value, body.payload, lead_id=body.lead_id, signals=body.signals)
            except (NormalizeError, ValueError) as exc:
                raise HTTPException(422, str(exc)) from exc
        return IntakeResponse(created=[summarize(p, {}) for p in packets])

    @app.post("/api/demo/load", response_model=IntakeResponse)
    def demo_load() -> IntakeResponse:
        with lock:
            return IntakeResponse(created=load_demo())

    if seed_demo:
        load_demo()

    if serve_web and (WEB_DIST / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            if path.startswith("api/"):
                raise HTTPException(404)
            candidate = (WEB_DIST / path).resolve()
            if path and candidate.is_file() and WEB_DIST.resolve() in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(WEB_DIST / "index.html")

    return app
