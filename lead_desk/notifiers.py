"""AgentNotifier delivery adapters: CLI | Email | WhatsApp | Telegram.

These tell the *agent* that a packet is waiting for review. They never message the customer:
the recipient comes only from AGENT_* settings and is refused if it equals the lead's own handle.
Without credentials, or while LEAD_DESK_NOTIFY_LIVE is false, every adapter runs in dry-run.
"""

from __future__ import annotations

import hashlib
import json
import re
import smtplib
import urllib.request
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Callable

from .config import Settings
from .schema import AgentPacket

Printer = Callable[[str], None]
MAX_CHAT_CHARS = 3500


class CustomerRecipientError(RuntimeError):
    """Raised when a notifier is pointed at the lead instead of the agent."""


@dataclass
class DeliveryResult:
    channel: str
    dry_run: bool
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
        lines += [f"  {i}. {m.listing.listing_id} {m.listing.title} €{m.listing.price_eur:,} — {'; '.join(m.reasons)}"
                  for i, m in enumerate(packet.matches, 1)]
    lines.append("Draft (copy and send yourself if you approve):")
    lines += ["  " + l for l in packet.draft_reply_for_agent.splitlines()]
    if not packet.guardrail.passed:
        lines.append(f"GUARDRAIL BLOCKED: {', '.join(packet.guardrail.hits)}")
    lines.append(f"Status: {packet.status.value} | packet {packet.packet_id} | reply approve/reject in Lead Desk")
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

    @property
    def configured(self) -> bool:
        return False

    @property
    def live(self) -> bool:
        return self.settings.notify_live and self.configured

    def notify(self, packet: AgentPacket) -> DeliveryResult:
        assert_agent_recipient(self.recipient, packet)
        digest = packet_digest(packet)
        if not self.live:
            why = "LEAD_DESK_NOTIFY_LIVE=false" if self.configured else "missing credentials"
            self.out(self.dry_run_preview(packet, digest, why))
            return DeliveryResult(self.name, True, self.recipient, digest, f"dry-run ({why})")
        detail = self.send(packet)
        return DeliveryResult(self.name, False, self.recipient, digest, detail)

    def dry_run_preview(self, packet: AgentPacket, digest: str, why: str) -> str:
        return (f"--- [dry-run:{self.name}] to agent={self.recipient or '<unset>'} ({why}) "
                f"packet={packet.packet_id} sha256={digest[:16]}\n{self.render(packet)}\n--- [end {self.name}]")

    def render(self, packet: AgentPacket) -> str:
        return agent_summary(packet)

    def send(self, packet: AgentPacket) -> str:
        raise NotImplementedError


class CLINotifier(AgentNotifier):
    name = "cli"

    def __init__(self, settings: Settings, out: Printer = print, show_json: bool = False):
        super().__init__(settings, out)
        self.show_json = show_json

    def notify(self, packet: AgentPacket) -> DeliveryResult:
        self.out(agent_summary(packet))
        if self.show_json:
            self.out(packet_json(packet))
        return DeliveryResult(self.name, False, "terminal", packet_digest(packet), "printed")


class EmailNotifier(AgentNotifier):
    name = "email"

    @property
    def recipient(self) -> str | None:
        return self.settings.agent_email_to

    @property
    def configured(self) -> bool:
        s = self.settings
        return bool(s.smtp_host and s.smtp_from and s.agent_email_to)

    def build_message(self, packet: AgentPacket) -> EmailMessage:
        msg = EmailMessage()
        msg["From"] = self.settings.smtp_from or "lead-desk@localhost"
        msg["To"] = self.recipient or "agent@localhost"
        msg["Subject"] = f"[Lead Desk] {packet.score.band.value} {packet.lead.lead_id} — review needed"
        msg.set_content(agent_summary(packet))
        msg.add_attachment(packet_json(packet).encode(), maintype="application", subtype="json",
                           filename=f"{packet.packet_id}.json")
        return msg

    def render(self, packet: AgentPacket) -> str:
        msg = self.build_message(packet)
        return (f"Subject: {msg['Subject']}\n{agent_summary(packet)}\n"
                f"[attachment {packet.packet_id}.json, {len(packet_json(packet).encode())} bytes]")

    def send(self, packet: AgentPacket) -> str:
        s = self.settings
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as smtp:
            smtp.starttls()
            if s.smtp_user and s.smtp_password:
                smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(self.build_message(packet))
        return "sent via SMTP"


def _post_json(url: str, body: dict, headers: dict[str, str] | None = None) -> str:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return f"HTTP {resp.status}"


class WhatsAppNotifier(AgentNotifier):
    """WhatsApp Cloud API text to the agent's own number (needs an open 24h window or a template)."""

    name = "whatsapp"

    @property
    def recipient(self) -> str | None:
        return self.settings.agent_whatsapp_to

    @property
    def configured(self) -> bool:
        s = self.settings
        return bool(s.whatsapp_token and s.whatsapp_phone_number_id and s.agent_whatsapp_to)

    def render(self, packet: AgentPacket) -> str:
        return agent_summary(packet)[:MAX_CHAT_CHARS]

    def send(self, packet: AgentPacket) -> str:
        s = self.settings
        url = f"https://graph.facebook.com/{s.whatsapp_api_version}/{s.whatsapp_phone_number_id}/messages"
        body = {"messaging_product": "whatsapp", "to": s.agent_whatsapp_to, "type": "text",
                "text": {"body": self.render(packet)}}
        return _post_json(url, body, {"Authorization": f"Bearer {s.whatsapp_token}"})


class TelegramNotifier(AgentNotifier):
    name = "telegram"

    @property
    def recipient(self) -> str | None:
        return self.settings.agent_telegram_chat_id

    @property
    def configured(self) -> bool:
        return bool(self.settings.telegram_bot_token and self.settings.agent_telegram_chat_id)

    def render(self, packet: AgentPacket) -> str:
        return agent_summary(packet)[:MAX_CHAT_CHARS]

    def send(self, packet: AgentPacket) -> str:
        s = self.settings
        url = f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage"
        return _post_json(url, {"chat_id": s.agent_telegram_chat_id, "text": self.render(packet)})


NOTIFIERS: dict[str, type[AgentNotifier]] = {
    "cli": CLINotifier, "email": EmailNotifier, "whatsapp": WhatsAppNotifier, "telegram": TelegramNotifier,
}


def build_notifiers(names: list[str], settings: Settings, out: Printer = print, show_json: bool = False) -> list[AgentNotifier]:
    result: list[AgentNotifier] = []
    for name in names:
        if name not in NOTIFIERS:
            raise ValueError(f"unknown notifier '{name}' (choose from {', '.join(NOTIFIERS)})")
        if name == "cli":
            result.append(CLINotifier(settings, out, show_json=show_json))
        else:
            result.append(NOTIFIERS[name](settings, out))
    return result
