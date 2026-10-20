"""One path: normalize -> score -> match -> packet -> notify agent -> (human) approve/reject."""

from __future__ import annotations

from typing import Any

from .config import Settings
from .intake.normalize import normalize
from .notifiers import AgentNotifier, DeliveryResult
from .packet import build_packet
from .property_match.matcher import filters_for_lead, match_listings
from .property_match.providers import ListingProvider, get_provider
from .schema import AgentPacket, Band, Intent, Lead, PacketStatus
from .scoring import logistics_notes, score_lead
from .storage.repository import LeadRepository


class LeadDesk:
    def __init__(self, settings: Settings, repo: LeadRepository, notifiers: list[AgentNotifier],
                 provider: ListingProvider | None = None):
        self.settings = settings
        self.repo = repo
        self.notifiers = notifiers
        self.provider = provider or get_provider(settings)

    def _should_match(self, band: Band, intent: Intent) -> bool:
        return band != Band.COLD and intent in (Intent.BUY, Intent.RENT)

    def build(self, lead: Lead) -> AgentPacket:
        score = score_lead(lead)
        self.repo.record_score(score)
        self.repo.bump_usage("scores")
        filters, matches = None, []
        if self._should_match(score.band, score.intent):
            filters = filters_for_lead(lead, score, exclude_ids=self.repo.rejected_listing_ids(lead.lead_id))
            if filters is not None:
                matches = match_listings(self.provider, filters, lead.budget_eur, limit=self.settings.max_matches)
                self.repo.bump_usage("listing_fetches")
        packet = build_packet(lead, score, notes=logistics_notes(lead), filters=filters, matches=matches)
        self.repo.save_packet(packet)
        return packet

    def notify(self, packet: AgentPacket) -> list[DeliveryResult]:
        results = []
        for notifier in self.notifiers:
            result = notifier.notify(packet)
            self.repo.add_event(packet.lead.lead_id, "notified", {
                "packet_id": packet.packet_id, "channel": result.channel, "packet_sha256": result.packet_sha256, "detail": result.detail,
            })
            results.append(result)
        self.repo.bump_usage("notifications", len(results))
        self.repo.conn.commit()
        return results

    def ingest(self, channel: str, payload: Any, *, lead_id: str | None = None,
               signals: dict[str, Any] | None = None) -> list[AgentPacket]:
        packets = []
        for lead in normalize(channel, payload, tenant_id=self.settings.tenant_id, lead_id=lead_id, signals=signals):
            lead = self.repo.upsert_lead(lead)
            packet = self.build(lead)
            self.notify(packet)
            packets.append(packet)
        return packets

    def rematch_after_rejection(self, packet: AgentPacket, listing_ids: list[str], agent_id: str) -> AgentPacket:
        """Agent rejected specific listings: exclude them for this lead and produce a fresh packet."""
        self.repo.reject_listings(packet.lead.lead_id, listing_ids, agent_id)
        self.repo.record_decision(packet, PacketStatus.REJECTED, agent_id,
                                  note=f"listings rejected: {', '.join(listing_ids)}; re-matched")
        new_packet = self.build(packet.lead)
        self.notify(new_packet)
        return new_packet
