"""AgentNotifier: how the *agent* learns a packet is waiting. Never addressed to the customer.

v1 ships the CLI desk only. Outbound agent channels (email, Telegram, ...) are out of scope until the
MVP has been tested on real situations; a future adapter subclasses `AgentNotifier`, sets
`recipient` from AGENT_* settings, and must call `assert_agent_recipient` before delivering.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Callable

from .config import Settings
from .schema import AgentPacket

Printer = Callable[[str], None]


class CustomerRecipientError(RuntimeError):
    """Raised when a notifier is pointed at the lead instead of the agent."""


@dataclass
class DeliveryResult:
    channel: str
    recipient: str | None
    packet_sha256: str
    detail: str


def packet_json(packet: AgentPacket) -> str:
    return json.dumps(packet.to_json_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def packet_digest(packet: AgentPacket) -> str:
    return hashlib.sha256(packet_json(packet).encode()).hexdigest()


def agent_summary(packet: AgentPacket) -> str:
    s, lead = packet.score, packet.lead
    lines = [
        f"[Lead Desk] {s.band.value} lead {lead.lead_id} ({lead.channel.value}/{lead.source}) — score {s.score_0_100}",
        f"Intent: {s.intent.value} | City: {lead.city or '?'} | Budget: {f'€{lead.budget_eur:,}' if lead.budget_eur else '?'}"
        f" | Timeline: {f'{lead.timeline_days} d' if lead.timeline_days is not None else '?'}",
        f"Why: {s.rationale}",
        f"Next action: {s.next_action}",
    ]
    lines += [f"Note: {n}" for n in packet.logistics_notes]
    if packet.matches:
        lines.append("Matches:")
        lines += [f"  {i}. {m.listing.listing_id} [{m.listing.source}] {m.listing.title} €{m.listing.price_eur:,}"
                  f" — {'; '.join(m.reasons)}" for i, m in enumerate(packet.matches, 1)]
    lines.append("Draft (copy and send yourself if you approve):")
    lines += ["  " + l for l in packet.draft_reply_for_agent.splitlines()]
    if not packet.guardrail.passed:
        lines.append(f"GUARDRAIL BLOCKED: {', '.join(packet.guardrail.hits)}")
    lines.append(f"Status: {packet.status.value} | packet {packet.packet_id}")
    return "\n".join(lines)


def _norm_handle(value: str | None) -> str:
    if not value:
        return ""
    v = value.strip().lower()
    digits = re.sub(r"\D", "", v)
    return digits if "@" not in v and len(digits) >= 6 else v


def assert_agent_recipient(recipient: str | None, packet: AgentPacket) -> None:
    if recipient and _norm_handle(recipient) == _norm_handle(packet.lead.contact_handle):
        raise CustomerRecipientError("Refusing to notify: recipient is the lead's own contact, not the agent.")


class AgentNotifier:
    name = "base"

    def __init__(self, settings: Settings, out: Printer = print):
        self.settings = settings
        self.out = out

    @property
    def recipient(self) -> str | None:
        return None

    def notify(self, packet: AgentPacket) -> DeliveryResult:
        raise NotImplementedError


class CLINotifier(AgentNotifier):
    name = "cli"

    def __init__(self, settings: Settings, out: Printer = print, show_json: bool = False):
        super().__init__(settings, out)
        self.show_json = show_json

    @property
    def recipient(self) -> str:
        return "terminal"

    def notify(self, packet: AgentPacket) -> DeliveryResult:
        assert_agent_recipient(self.recipient, packet)
        self.out(agent_summary(packet))
        if self.show_json:
            self.out(packet_json(packet))
        return DeliveryResult(self.name, self.recipient, packet_digest(packet), "printed")
