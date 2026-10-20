"""Settings from environment variables (optionally loaded from a `.env` file).

Every external service is optional. See `.env.example` (repo root) and `lead_desk/README.md`.
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
    max_matches: int = 3

    telegram_webhook_secret: str | None = None

    imap_host: str | None = None
    imap_port: int = 993
    imap_user: str | None = None
    imap_password: str | None = None
    imap_folder: str = "INBOX"

    idealista_api_key: str | None = None
    idealista_api_secret: str | None = None
    idealista_country: str = "pt"
    idealista_max_items: int = 50
    idealista_default_radius_km: float = 10.0

    feature_scrape_listings: bool = False

    @property
    def idealista_configured(self) -> bool:
        return bool(self.idealista_api_key and self.idealista_api_secret)


def load_settings(env_file: str | Path | None = None) -> Settings:
    if load_dotenv is not None:
        load_dotenv(env_file or Path.cwd() / ".env", override=False)
    return Settings(
        db_path=_str("LEAD_DESK_DB_PATH") or "lead_desk.sqlite3",
        tenant_id=_str("LEAD_DESK_TENANT_ID") or "tenant_demo",
        max_matches=int(_str("LEAD_DESK_MAX_MATCHES") or 3),
        telegram_webhook_secret=_str("TELEGRAM_WEBHOOK_SECRET"),
        imap_host=_str("IMAP_HOST"),
        imap_port=int(_str("IMAP_PORT") or 993),
        imap_user=_str("IMAP_USER"),
        imap_password=_str("IMAP_PASSWORD"),
        imap_folder=_str("IMAP_FOLDER") or "INBOX",
        idealista_api_key=_str("IDEALISTA_API_KEY"),
        idealista_api_secret=_str("IDEALISTA_API_SECRET"),
        idealista_country=_str("IDEALISTA_COUNTRY") or "pt",
        idealista_max_items=int(_str("IDEALISTA_MAX_ITEMS") or 50),
        idealista_default_radius_km=float(_str("IDEALISTA_DEFAULT_RADIUS_KM") or 10),
        feature_scrape_listings=_bool(os.getenv("FEATURE_SCRAPE_LISTINGS"), False),
    )
