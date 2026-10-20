"""Human-in-the-loop review. The agent decides; the system never contacts the customer.

`approve_packet` / `reject_packet` are the single decision path, shared by the CLI prompt and the web API.
"""

from __future__ import annotations

from typing import Callable

from .pipeline import LeadDesk
from .schema import AgentPacket, PacketStatus

PROMPT = "Decision for {lead} [a]pprove | [r]eject | r <listing_id ...> reject listings & re-match | [s]kip > "
MAX_ROUNDS = 5

InputFn = Callable[[str], str]


class DecisionError(ValueError):
    """The requested decision is not allowed for this packet."""


def approve_packet(desk: LeadDesk, packet: AgentPacket, agent_id: str, note: str | None = None) -> AgentPacket:
    if packet.status == PacketStatus.BLOCKED_GUARDRAIL:
        raise DecisionError("Cannot approve: the guardrail blocked this packet. Rewrite manually or reject.")
    if packet.status != PacketStatus.PENDING_REVIEW:
        raise DecisionError(f"Packet {packet.packet_id} is already {packet.status.value}.")
    return desk.repo.record_decision(packet, PacketStatus.APPROVED, agent_id, note=note or "approved to present listings")


def reject_packet(desk: LeadDesk, packet: AgentPacket, agent_id: str, listing_ids: list[str] | None = None,
                  note: str | None = None) -> AgentPacket:
    """No listing ids: reject the whole packet. With ids: exclude those listings and return a fresh packet."""
    if packet.status not in (PacketStatus.PENDING_REVIEW, PacketStatus.BLOCKED_GUARDRAIL):
        raise DecisionError(f"Packet {packet.packet_id} is already {packet.status.value}.")
    listing_ids = [i for i in (listing_ids or []) if i]
    known = {m.listing.listing_id for m in packet.matches}
    unknown = [i for i in listing_ids if i not in known]
    if unknown:
        raise DecisionError(f"Unknown listing id(s) for this packet: {', '.join(unknown)}")
    if listing_ids:
        return desk.rematch_after_rejection(packet, listing_ids, agent_id)
    return desk.repo.record_decision(packet, PacketStatus.REJECTED, agent_id, note=note or "agent rejected packet")


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
            try:
                packet = approve_packet(desk, packet, agent_id)
            except DecisionError as exc:
                out(f"  {exc}")
                continue
            out(f"  APPROVED by {agent_id}. Nothing was sent to the customer — copy the draft and send it "
                "yourself from your own phone, email or CRM.")
            return packet

        if cmd in ("r", "reject"):
            listing_ids = parts[1:]
            try:
                packet = reject_packet(desk, packet, agent_id, listing_ids)
            except DecisionError as exc:
                out(f"  {exc}")
                continue
            if listing_ids:
                out(f"  Excluded {', '.join(listing_ids)} for {packet.lead.lead_id}; new packet {packet.packet_id} above.")
                continue
            out(f"  REJECTED by {agent_id}. Listings will not be presented. The lead itself is kept (never 'rejected as a person').")
            return packet

        if cmd in ("s", "skip"):
            out("  Skipped — left pending.")
            return packet
        out("  Please type a, r, r <listing_id ...>, or s.")
    out("  Too many rounds — left pending.")
    return packet
