"""`python -m lead_desk <command>` — CLI for the Lead Desk vertical slice.

  demo           synthetic payload file -> normalize -> score -> match -> agent packet -> approve/reject
  ingest         one payload file for a given channel
  imap-poll      email intake from IMAP (or the sample .eml inbox when IMAP is not configured)
  serve-webhooks Telegram webhook stub server
  serve-api      FastAPI backend + web dashboard (web/dist) on http://127.0.0.1:8000
  review         approve/reject pending packets stored in the database
  leads          list stored leads
  export-lead    print everything stored about one lead as JSON
  delete-lead    erase one lead with its packets, decisions and events
  purge          erase leads inactive for longer than the retention period
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Settings, load_settings
from .hitl import review_packet
from .intake.imap_poll import SAMPLE_INBOX, fetch_unseen, imap_configured, read_eml_dir
from .notifiers import CLINotifier
from .pipeline import LeadDesk
from .storage.repository import LeadRepository

DEFAULT_PAYLOADS = Path(__file__).resolve().parent / "data" / "synthetic_payloads.json"
RULE = "=" * 78


def _desk(settings: Settings, db: str, show_json: bool) -> LeadDesk:
    repo = LeadRepository(db, tenant_id=settings.tenant_id)
    return LeadDesk(settings, repo, [CLINotifier(settings, show_json=show_json)])


def _review_all(desk: LeadDesk, packets, agent_id: str) -> None:
    for packet in packets:
        review_packet(desk, packet, agent_id=agent_id)


def _summary(desk: LeadDesk) -> None:
    print(RULE)
    print("Decisions recorded (lead_events):")
    latest: dict[str, tuple[str, str]] = {}
    for row in desk.repo.conn.execute(
        "SELECT p.lead_id, p.status, l.latest_band FROM packets p JOIN leads l USING(lead_id) ORDER BY p.created_at"
    ):
        latest[row["lead_id"]] = (row["latest_band"], row["status"])
    for lead_id, (band, status) in sorted(latest.items()):
        print(f"  {lead_id:<16} band={band:<5} latest_packet={status}")
    print("No message was sent to any customer or agent: the CLI desk is the only delivery channel.")


def cmd_demo(args: argparse.Namespace, settings: Settings) -> int:
    desk = _desk(settings, args.db, args.json)
    envelopes = json.loads(Path(args.payloads).read_text(encoding="utf-8"))
    print(f"Lead Desk demo — {len(envelopes)} synthetic payloads from {args.payloads}")
    print(f"Listings provider: {desk.provider.name}")
    for env in envelopes:
        print(RULE)
        print(f"INBOUND {env['channel']}: {env.get('note', '')}")
        packets = desk.ingest(env["channel"], env["payload"], lead_id=env.get("lead_id"), signals=env.get("signals"))
        if not args.no_review:
            _review_all(desk, packets, args.agent)
    _summary(desk)
    return 0


def cmd_ingest(args: argparse.Namespace, settings: Settings) -> int:
    desk = _desk(settings, args.db, args.json)
    raw = Path(args.file).read_bytes()
    payload = raw if args.channel == "email" else json.loads(raw)
    packets = desk.ingest(args.channel, payload, lead_id=args.lead_id)
    print(f"{len(packets)} packet(s) stored as pending_review in {args.db}")
    return 0


def cmd_imap(args: argparse.Namespace, settings: Settings) -> int:
    desk = _desk(settings, args.db, args.json)
    if imap_configured(settings) and not args.eml_dir:
        messages = [(f"imap:{i}", m) for i, m in enumerate(fetch_unseen(settings))]
    else:
        directory = Path(args.eml_dir) if args.eml_dir else SAMPLE_INBOX
        print(f"IMAP not configured (or --eml-dir given): reading .eml files from {directory}")
        messages = list(read_eml_dir(directory))
    for name, raw in messages:
        print(RULE)
        print(f"INBOUND email {name}")
        desk.ingest("email", raw)
    print(f"{len(messages)} email(s) processed into {args.db}")
    return 0


def cmd_review(args: argparse.Namespace, settings: Settings) -> int:
    desk = _desk(settings, args.db, args.json)
    pending = desk.repo.pending_packets()
    print(f"{len(pending)} packet(s) pending review in {args.db}")
    for packet in pending:
        print(RULE)
        desk.notifiers[0].notify(packet)
        review_packet(desk, packet, agent_id=args.agent)
    return 0


def cmd_leads(args: argparse.Namespace, settings: Settings) -> int:
    repo = LeadRepository(args.db, tenant_id=settings.tenant_id)
    for row in repo.list_leads(band=args.band):
        print(json.dumps(row, ensure_ascii=False))
    return 0


def cmd_export_lead(args: argparse.Namespace, settings: Settings) -> int:
    repo = LeadRepository(args.db, tenant_id=settings.tenant_id)
    data = repo.export_lead(args.lead_id)
    if data is None:
        print(f"Lead {args.lead_id} not found in {args.db}", file=sys.stderr)
        return 1
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"Exported {args.lead_id} to {args.out}")
    else:
        print(text)
    return 0


def cmd_delete_lead(args: argparse.Namespace, settings: Settings) -> int:
    repo = LeadRepository(args.db, tenant_id=settings.tenant_id)
    if not args.yes:
        answer = input(f"Erase {args.lead_id} and all its packets, decisions and events from {args.db}? [y/N] ")
        if answer.strip().lower() not in {"y", "yes"}:
            print("Nothing deleted.")
            return 1
    counts = repo.delete_lead(args.lead_id, actor=f"agent:{args.agent}")
    if counts is None:
        print(f"Lead {args.lead_id} not found in {args.db}", file=sys.stderr)
        return 1
    print(f"Erased {args.lead_id}: " + ", ".join(f"{n} {table}" for table, n in counts.items()))
    return 0


def cmd_purge(args: argparse.Namespace, settings: Settings) -> int:
    days = args.days or settings.retention_days
    if not days:
        print("No retention period: pass --days or set LEAD_DESK_RETENTION_DAYS.", file=sys.stderr)
        return 2
    repo = LeadRepository(args.db, tenant_id=settings.tenant_id)
    lead_ids = repo.purge_inactive(days, dry_run=args.dry_run)
    verb = "Would erase" if args.dry_run else "Erased"
    print(f"{verb} {len(lead_ids)} lead(s) inactive for more than {days} days" + (": " + ", ".join(lead_ids) if lead_ids else ""))
    return 0


def cmd_serve_api(args: argparse.Namespace, settings: Settings) -> int:
    import uvicorn

    from .api import create_app

    desk = LeadDesk(settings, LeadRepository(args.db, tenant_id=settings.tenant_id), notifiers=[])
    app = create_app(settings, desk=desk, seed_demo=args.seed_demo)
    print(f"Lead Desk dashboard on http://{args.host}:{args.port} (API docs at /docs, db={args.db})", flush=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def cmd_serve(args: argparse.Namespace, settings: Settings) -> int:
    from .intake.webhooks import make_server

    desk = _desk(settings, args.db, args.json)
    server = make_server(desk, args.host, args.port)
    print(f"Webhook stub listening on http://{args.host}:{args.port} (POST /webhooks/telegram)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m lead_desk", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", default=None, help="path to a .env file (default: ./.env)")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser, db_default: str | None) -> None:
        p.add_argument("--db", default=db_default, help="SQLite path (':memory:' for a throwaway run)")
        p.add_argument("--json", action="store_true", help="also print the full packet JSON")
        p.add_argument("--agent", default="agent_demo", help="agent id recorded on decisions")

    p = sub.add_parser("demo", help="end-to-end CLI demo on synthetic payloads")
    common(p, ":memory:")
    p.add_argument("--payloads", default=str(DEFAULT_PAYLOADS))
    p.add_argument("--no-review", action="store_true", help="skip the approve/reject prompts")
    p.set_defaults(func=cmd_demo)

    p = sub.add_parser("ingest", help="ingest one payload file")
    common(p, None)
    p.add_argument("--channel", required=True, choices=["email", "telegram"])
    p.add_argument("--file", required=True)
    p.add_argument("--lead-id", default=None)
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("imap-poll", help="email intake via IMAP or sample .eml files")
    common(p, None)
    p.add_argument("--eml-dir", default=None)
    p.set_defaults(func=cmd_imap)

    p = sub.add_parser("serve-webhooks", help="Telegram webhook stub")
    common(p, None)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8787)
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("serve-api", help="FastAPI backend + web dashboard")
    common(p, None)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--seed-demo", action="store_true", help="load the synthetic demo payloads on start")
    p.set_defaults(func=cmd_serve_api)

    p = sub.add_parser("review", help="approve/reject pending packets")
    common(p, None)
    p.set_defaults(func=cmd_review)

    p = sub.add_parser("leads", help="list stored leads")
    common(p, None)
    p.add_argument("--band", choices=["HOT", "WARM", "COLD"])
    p.set_defaults(func=cmd_leads)

    p = sub.add_parser("export-lead", help="print everything stored about one lead as JSON")
    common(p, None)
    p.add_argument("lead_id")
    p.add_argument("--out", default=None, help="write to this file instead of stdout")
    p.set_defaults(func=cmd_export_lead)

    p = sub.add_parser("delete-lead", help="erase one lead and everything linked to it")
    common(p, None)
    p.add_argument("lead_id")
    p.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    p.set_defaults(func=cmd_delete_lead)

    p = sub.add_parser("purge", help="erase leads inactive for longer than the retention period")
    common(p, None)
    p.add_argument("--days", type=int, default=None, help="retention in days (default: LEAD_DESK_RETENTION_DAYS)")
    p.add_argument("--dry-run", action="store_true", help="list what would be erased without deleting")
    p.set_defaults(func=cmd_purge)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings(args.env_file)
    if getattr(args, "db", None) is None:
        args.db = settings.db_path
    return args.func(args, settings)


if __name__ == "__main__":
    sys.exit(main())
