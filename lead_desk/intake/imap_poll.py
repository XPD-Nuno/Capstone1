"""Email intake: poll an IMAP mailbox, or read `.eml` files when no IMAP credentials are set.

Read-only towards the customer: we fetch and mark messages as seen, we never reply.
"""

from __future__ import annotations

import imaplib
from pathlib import Path
from typing import Iterator

from ..config import Settings

SAMPLE_INBOX = Path(__file__).resolve().parents[1] / "data" / "sample_inbox"


def imap_configured(settings: Settings) -> bool:
    return bool(settings.imap_host and settings.imap_user and settings.imap_password)


def fetch_unseen(settings: Settings, limit: int = 50) -> Iterator[bytes]:
    with imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port) as imap:
        imap.login(settings.imap_user, settings.imap_password)
        imap.select(settings.imap_folder)
        status, data = imap.search(None, "UNSEEN")
        if status != "OK":
            return
        for num in data[0].split()[:limit]:
            status, parts = imap.fetch(num, "(RFC822)")
            if status == "OK" and parts and isinstance(parts[0], tuple):
                yield parts[0][1]


def read_eml_dir(directory: Path = SAMPLE_INBOX) -> Iterator[tuple[str, bytes]]:
    for path in sorted(directory.glob("*.eml")):
        yield path.name, path.read_bytes()
