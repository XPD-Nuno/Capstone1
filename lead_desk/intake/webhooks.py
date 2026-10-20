"""Inbound Telegram webhook stub (stdlib only) feeding the same pipeline.

  POST /webhooks/telegram   Bot API Update; X-Telegram-Bot-Api-Secret-Token checked when TELEGRAM_WEBHOOK_SECRET is set
  GET  /healthz

Packets are stored as pending_review; decisions happen in `lead_desk review`.
WhatsApp intake is deferred until after real MVP tests.
This is a demo stub: put it behind HTTPS (reverse proxy / tunnel) before pointing Telegram at it.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from ..pipeline import LeadDesk
from .normalize import NormalizeError


def handle_webhook(desk: LeadDesk, method: str, path: str, headers: dict[str, str], body: bytes) -> tuple[int, dict[str, Any] | str]:
    """Framework-free handler so it can be unit-tested and reused behind any HTTP server."""
    url = urlparse(path)
    s = desk.settings
    h = {k.lower(): v for k, v in headers.items()}

    if method == "GET" and url.path == "/healthz":
        return 200, {"ok": True}

    if url.path == "/webhooks/telegram" and method == "POST":
        if s.telegram_webhook_secret and h.get("x-telegram-bot-api-secret-token") != s.telegram_webhook_secret:
            return 401, {"error": "bad secret token"}
        return _ingest(desk, "telegram", body)

    return 404, {"error": "not found"}


def _ingest(desk: LeadDesk, channel: str, body: bytes) -> tuple[int, dict[str, Any]]:
    try:
        payload = json.loads(body or b"{}")
        packets = desk.ingest(channel, payload)
    except (json.JSONDecodeError, NormalizeError) as exc:
        # 200 so the platform does not retry forever on payloads we will never parse.
        return 200, {"ignored": str(exc)}
    return 200, {"packets": [{"packet_id": p.packet_id, "lead_id": p.lead.lead_id, "band": p.score.band.value,
                              "status": p.status.value} for p in packets]}


def make_server(desk: LeadDesk, host: str = "127.0.0.1", port: int = 8787) -> ThreadingHTTPServer:
    lock = threading.Lock()  # sqlite connection is shared

    class Handler(BaseHTTPRequestHandler):
        def _respond(self, method: str) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            try:
                with lock:
                    status, payload = handle_webhook(desk, method, self.path, dict(self.headers), body)
            except Exception as exc:  # keep the server up; the platform will retry on 5xx
                status, payload = 500, {"error": type(exc).__name__}
            data = payload.encode() if isinstance(payload, str) else json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/plain" if isinstance(payload, str) else "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            self._respond("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._respond("POST")

        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"[webhook] {self.address_string()} {fmt % args}", flush=True)

    return ThreadingHTTPServer((host, port), Handler)
