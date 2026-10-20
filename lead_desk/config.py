"""Settings from environment variables (optionally loaded from a `.env` file).

Every external channel is optional. Missing keys => that notifier runs in dry-run.
See `.env.example` (repo root) and `lead_desk/README.md` for the variable list.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional
    load_dotenv = None


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _str(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    return value.strip()


@dataclass(frozen=True)
class Settings:
    db_path: str = "lead_desk.sqlite3"
    tenant_id: str = "tenant_demo"
    agency_sales_led: bool = True
    max_matches: int = 3

    # Global kill switch: even with keys present, nothing leaves the machine unless this is true.
    notify_live: bool = False

    # Agent notification targets (the AGENT's own inbox / phone / chat — never the customer).
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    agent_email_to: str | None = None

    whatsapp_token: str | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_api_version: str = "v20.0"
    agent_whatsapp_to: str | None = None
    whatsapp_verify_token: str | None = None
    whatsapp_app_secret: str | None = None

    telegram_bot_token: str | None = None
    agent_telegram_chat_id: str | None = None
    telegram_webhook_secret: str | None = None

    imap_host: str | None = None
    imap_port: int = 993
    imap_user: str | None = None
    imap_password: str | None = None
    imap_folder: str = "INBOX"

    feature_partner_api: bool = False
    feature_scrape_listings: bool = False


def load_settings(env_file: str | Path | None = None) -> Settings:
    if load_dotenv is not None:
        load_dotenv(env_file or Path.cwd() / ".env", override=False)
    return Settings(
        db_path=_str("LEAD_DESK_DB_PATH") or "lead_desk.sqlite3",
        tenant_id=_str("LEAD_DESK_TENANT_ID") or "tenant_demo",
        agency_sales_led=_bool(os.getenv("LEAD_DESK_SALES_LED"), True),
        max_matches=int(_str("LEAD_DESK_MAX_MATCHES") or 3),
        notify_live=_bool(os.getenv("LEAD_DESK_NOTIFY_LIVE"), False),
        smtp_host=_str("SMTP_HOST"),
        smtp_port=int(_str("SMTP_PORT") or 587),
        smtp_user=_str("SMTP_USER"),
        smtp_password=_str("SMTP_PASSWORD"),
        smtp_from=_str("SMTP_FROM"),
        agent_email_to=_str("AGENT_EMAIL_TO"),
        whatsapp_token=_str("WHATSAPP_TOKEN"),
        whatsapp_phone_number_id=_str("WHATSAPP_PHONE_NUMBER_ID"),
        whatsapp_api_version=_str("WHATSAPP_API_VERSION") or "v20.0",
        agent_whatsapp_to=_str("AGENT_WHATSAPP_TO"),
        whatsapp_verify_token=_str("WHATSAPP_VERIFY_TOKEN"),
        whatsapp_app_secret=_str("WHATSAPP_APP_SECRET"),
        telegram_bot_token=_str("TELEGRAM_BOT_TOKEN"),
        agent_telegram_chat_id=_str("AGENT_TELEGRAM_CHAT_ID"),
        telegram_webhook_secret=_str("TELEGRAM_WEBHOOK_SECRET"),
        imap_host=_str("IMAP_HOST"),
        imap_port=int(_str("IMAP_PORT") or 993),
        imap_user=_str("IMAP_USER"),
        imap_password=_str("IMAP_PASSWORD"),
        imap_folder=_str("IMAP_FOLDER") or "INBOX",
        feature_partner_api=_bool(os.getenv("FEATURE_PARTNER_LISTINGS_API"), False),
        feature_scrape_listings=_bool(os.getenv("FEATURE_SCRAPE_LISTINGS"), False),
    )
