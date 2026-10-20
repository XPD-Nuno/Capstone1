"""Human-in-the-loop review. The agent decides; the system never contacts the customer."""

from __future__ import annotations

from typing import Callable

from .pipeline import LeadDesk
from .schema import AgentPacket, PacketStatus

PROMPT = "Decision for {lead} [a]pprove | [r]eject | r <listing_id ...> reject listings & re-match | [s]kip > "
MAX_ROUNDS = 5

InputFn = Callable[[str], str]


def review_packet(desk: LeadDesk, packet: AgentPacket, *, agent_id: str = "agent_demo",
                  input_fn: InputFn | None = None, out: Callable[[str], None] = print) -> AgentPacket:
    input_fn = input_fn or input
    for _ in range(MAX_ROUNDS):
        try:
            raw = input_fn(PROMPT.format(lead=packet.lead.lead_id)).strip()
        except EOFError:
            out("  (no input — left pending for `python -m lead_desk review`)")
            return packet
        parts = raw.split()
        cmd = parts[0].lower() if parts else "s"

        if cmd in ("a", "approve"):
            if packet.status == PacketStatus.BLOCKED_GUARDRAIL:
                out("  Cannot approve: the guardrail blocked this packet. Rewrite manually or reject.")
                continue
            packet = desk.repo.record_decision(packet, PacketStatus.APPROVED, agent_id, note="approved to present listings")
            out(f"  APPROVED by {agent_id}. Nothing was sent to the customer — copy the draft and send it "
                "yourself from your own WhatsApp / email / CRM.")
            return packet

        if cmd in ("r", "reject"):
            listing_ids = [p for p in parts[1:] if p]
            known = {m.listing.listing_id for m in packet.matches}
            unknown = [i for i in listing_ids if i not in known]
            if unknown:
                out(f"  Unknown listing id(s) for this packet: {', '.join(unknown)}")
                continue
            if listing_ids:
                packet = desk.rematch_after_rejection(packet, listing_ids, agent_id)
                out(f"  Excluded {', '.join(listing_ids)} for {packet.lead.lead_id}; new packet {packet.packet_id} above.")
                continue
            packet = desk.repo.record_decision(packet, PacketStatus.REJECTED, agent_id, note="agent rejected packet")
            out(f"  REJECTED by {agent_id}. Listings will not be presented. The lead itself is kept (never 'rejected as a person').")
            return packet

        if cmd in ("s", "skip"):
            out("  Skipped — left pending.")
            return packet
        out("  Please type a, r, r <listing_id ...>, or s.")
    out("  Too many rounds — left pending.")
    return packet
