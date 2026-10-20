"""Channel adapters: email | whatsapp | telegram -> `Lead`.

Each parser accepts the channel's native payload shape:
- email: raw RFC 822 text/bytes (what IMAP returns) or a simple dict {from, subject, body, message_id}
- whatsapp: WhatsApp Business Cloud API webhook body (entry[].changes[].value.messages[])
- telegram: Telegram Bot API `Update` object
"""

from __future__ import annotations

import hashlib
import html
import re
from email import message_from_bytes, policy
from email.message import EmailMessage
from email.utils import parseaddr
from typing import Any

from ..schema import Channel, Lead
from .extract import (
    extract_budget_eur,
    extract_city,
    extract_listing_ref,
    extract_preferences,
    extract_timeline_days,
    mentions_phone,
)

PORTAL_DOMAINS = {
    "idealista.pt": "idealista", "idealista.com": "idealista",
    "imovirtual.com": "imovirtual", "casa.sapo.pt": "casasapo", "supercasa.pt": "supercasa",
}

SIGNAL_FIELDS = ("property_views_7d", "saved_listings", "replied_to_agent", "phone_provided")


class NormalizeError(ValueError):
    pass


def dedup_key_for(channel: Channel, handle: str | None) -> str | None:
    if not handle:
        return None
    norm = handle.strip().lower()
    if channel in (Channel.WHATSAPP,) or re.fullmatch(r"\+?[\d\s.-]{7,}", norm):
        norm = "tel:" + re.sub(r"\D", "", norm)
    elif channel == Channel.TELEGRAM:
        norm = "tg:" + norm
    else:
        norm = "mail:" + norm
    return hashlib.sha256(norm.encode()).hexdigest()[:16]


def synthetic_lead_id(tenant_id: str, dedup_key: str | None, fallback: str) -> str:
    basis = f"{tenant_id}|{dedup_key or fallback}"
    return "lead_" + hashlib.sha1(basis.encode()).hexdigest()[:10]


def _build_lead(
    *,
    channel: Channel,
    message: str,
    handle: str | None,
    source: str,
    raw_ref: str | None,
    tenant_id: str,
    lead_id: str | None,
    replied: bool = False,
    phone: bool = False,
    email: bool = False,
    signals: dict[str, Any] | None = None,
    context_text: str | None = None,
) -> Lead:
    if not message or not message.strip():
        raise NormalizeError(f"{channel.value}: empty message body")
    dedup = dedup_key_for(channel, handle)
    data: dict[str, Any] = dict(
        lead_id=lead_id or synthetic_lead_id(tenant_id, dedup, raw_ref or message),
        tenant_id=tenant_id,
        channel=channel,
        source=source,
        contact_handle=handle,
        dedup_key=dedup,
        portal_listing_ref=extract_listing_ref(context_text or message),
        city=extract_city(message),
        message=message,
        budget_eur=extract_budget_eur(message),
        timeline_days=extract_timeline_days(message),
        replied_to_agent=replied,
        phone_provided=phone or mentions_phone(message),
        email_provided=email,
        preferences=extract_preferences(message),
        raw_ref=raw_ref,
    )
    for key, value in (signals or {}).items():
        if key in SIGNAL_FIELDS or key in ("budget_eur", "timeline_days", "city", "source"):
            data[key] = value
    return Lead(**data)


# ---------------------------------------------------------------- email


def _strip_html(body: str) -> str:
    body = re.sub(r"(?is)<(script|style).*?</\1>", " ", body)
    body = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", body)
    return html.unescape(re.sub(r"<[^>]+>", " ", body))


def _email_text(msg: EmailMessage) -> str:
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    content = part.get_content()
    return _strip_html(content) if part.get_content_type() == "text/html" else content


def _portal_source(address: str) -> str | None:
    domain = address.rsplit("@", 1)[-1].lower()
    for known, name in PORTAL_DOMAINS.items():
        if domain == known or domain.endswith("." + known):
            return name
    return None


_LABEL = r"^\s*{label}\s*:\s*(.+)$"


def _labelled(body: str, *labels: str) -> str | None:
    for label in labels:
        m = re.search(_LABEL.format(label=label), body, re.IGNORECASE | re.MULTILINE)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return None


def _portal_message(body: str) -> str:
    """Portal notifications wrap the enquiry; keep only the customer's words when labelled."""
    m = re.search(r"^\s*(mensagem|message)\s*:\s*(.*?)(?=^\s*[A-Za-zÀ-ÿ ]{2,20}:\s|\Z)", body, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    return m.group(2).strip() if m and m.group(2).strip() else body.strip()


def parse_email(payload: str | bytes | dict[str, Any], *, tenant_id: str = "tenant_demo",
                lead_id: str | None = None, signals: dict[str, Any] | None = None) -> Lead:
    if isinstance(payload, dict):
        sender = payload.get("from", "")
        subject = payload.get("subject", "")
        body = payload.get("body", "")
        message_id = payload.get("message_id")
    else:
        raw = payload.encode("utf-8") if isinstance(payload, str) else payload
        msg = message_from_bytes(raw, policy=policy.default)
        sender = str(msg.get("From", ""))
        subject = str(msg.get("Subject", ""))
        body = _email_text(msg)  # type: ignore[arg-type]
        message_id = msg.get("Message-ID")

    sender_addr = parseaddr(sender)[1]
    portal = _portal_source(sender_addr)
    handle = sender_addr or None
    message = body.strip()
    phone = False
    if portal:
        handle = _labelled(body, "email", "e-mail") or handle
        phone = bool(_labelled(body, "telefone", "telemóvel", "telemovel", "phone", "tel"))
        message = _portal_message(body)
    if subject and not portal and subject.lower() not in message.lower():
        message = f"{subject.strip()}\n{message}"
    replied = bool(re.match(r"^\s*(re|res|resp)\s*:", subject or "", re.IGNORECASE))
    return _build_lead(
        channel=Channel.EMAIL, message=message, handle=handle, source=portal or "direct_email",
        raw_ref=message_id, tenant_id=tenant_id, lead_id=lead_id, replied=replied, phone=phone,
        email=bool(handle and "@" in handle), signals=signals, context_text=body,
    )


# ---------------------------------------------------------------- whatsapp


def parse_whatsapp(payload: dict[str, Any], *, tenant_id: str = "tenant_demo",
                   lead_id: str | None = None, signals: dict[str, Any] | None = None) -> list[Lead]:
    """Returns one Lead per inbound text message. Status callbacks and media are ignored."""
    if payload.get("object") != "whatsapp_business_account":
        raise NormalizeError("whatsapp: not a whatsapp_business_account webhook")
    leads: list[Lead] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                if msg.get("type") != "text":
                    continue
                leads.append(_build_lead(
                    channel=Channel.WHATSAPP, message=msg.get("text", {}).get("body", ""),
                    handle=msg.get("from"), source="whatsapp", raw_ref=msg.get("id"),
                    tenant_id=tenant_id, lead_id=lead_id, replied="context" in msg,
                    phone=True, signals=signals,
                ))
    return leads


# ---------------------------------------------------------------- telegram


def parse_telegram(payload: dict[str, Any], *, tenant_id: str = "tenant_demo",
                   lead_id: str | None = None, signals: dict[str, Any] | None = None) -> Lead | None:
    """Returns None for updates without user text (joins, stickers, bot messages)."""
    msg = payload.get("message") or payload.get("edited_message")
    if not msg or not msg.get("text") or msg.get("from", {}).get("is_bot"):
        return None
    text = msg["text"]
    if text.startswith("/start"):
        return None
    chat_id = msg.get("chat", {}).get("id")
    return _build_lead(
        channel=Channel.TELEGRAM, message=text, handle=str(chat_id) if chat_id is not None else None,
        source="telegram", raw_ref=f"tg:{payload.get('update_id')}", tenant_id=tenant_id,
        lead_id=lead_id, replied="reply_to_message" in msg, signals=signals,
    )


def normalize(channel: str | Channel, payload: Any, *, tenant_id: str = "tenant_demo",
              lead_id: str | None = None, signals: dict[str, Any] | None = None) -> list[Lead]:
    ch = Channel(channel)
    kwargs = dict(tenant_id=tenant_id, lead_id=lead_id, signals=signals)
    if ch == Channel.EMAIL:
        return [parse_email(payload, **kwargs)]
    if ch == Channel.WHATSAPP:
        return parse_whatsapp(payload, **kwargs)
    lead = parse_telegram(payload, **kwargs)
    return [lead] if lead else []
