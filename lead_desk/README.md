# Lead Desk — vertical slice

One path, end to end: **inbound message → normalize → score (HOT/WARM/COLD + why) → match properties → agent packet → agent approves or rejects**.

- The system **never contacts the customer**. Notifiers (CLI / Email / WhatsApp / Telegram) tell the *agent* a packet is waiting. The agent copies the draft and sends it from their own WhatsApp, email or CRM.
- Scoring uses operational signals only (intent, budget, timing, search activity, contactability). Nationality, neighbourhood and language ability are never inputs, and a guardrail blocks any system text that mentions a banned attribute.
- All demo data is synthetic: `lead_*` ids, `@example.invalid` addresses, placeholder WhatsApp/Telegram ids, `mock_lst_*` listings.
- This is a first-pass build. It does not certify anything under GDPR or the EU AI Act.

## Run the demo

```bash
pip install -r lead_desk/requirements.txt
python -m lead_desk demo
```

The demo reads `lead_desk/data/synthetic_payloads.json` (7 payloads: Idealista-style email, direct email, WhatsApp Cloud API webhooks, Telegram updates). For each one it prints the agent packet and asks:

```
[a]pprove | [r]eject | r <listing_id ...> reject listings & re-match | [s]kip
```

- `a`: marks the packet as approved to present. Nothing is sent to anyone.
- `r`: rejects the packet. The lead is kept; only the listings are not presented.
- `r mock_lst_001`: excludes that listing for this lead (stored in `rejected_listings`) and re-matches.
- `s` / end of input: leaves the packet as `pending_review`.

Useful flags:

| Command | What it shows |
| --- | --- |
| `python -m lead_desk demo --notify all` | The same packet going through the CLI, Email, WhatsApp and Telegram notifiers. Without keys they run in dry-run, and every preview prints the packet's sha256 |
| `python -m lead_desk demo --json` | Also prints the full packet JSON |
| `python -m lead_desk demo --no-review` | No prompts (CI / screenshots) |
| `printf 'a\nr\ns\n' \| python -m lead_desk demo` | Scripted decisions |
| `python -m lead_desk demo --db lead_desk.sqlite3` | Keep the database (the default is in-memory) |

## Other commands

```bash
python -m lead_desk imap-poll --db lead_desk.sqlite3           # IMAP if configured, else data/sample_inbox/*.eml
python -m lead_desk ingest --channel whatsapp --file payload.json --db lead_desk.sqlite3
python -m lead_desk serve-webhooks --db lead_desk.sqlite3 --notify cli,telegram   # :8787
python -m lead_desk review --db lead_desk.sqlite3              # approve/reject everything pending
python -m lead_desk leads --db lead_desk.sqlite3 --band HOT
```

Webhook endpoints (stdlib server, demo-grade; put it behind HTTPS before pointing Meta or Telegram at it):

| Endpoint | Check |
| --- | --- |
| `GET /webhooks/whatsapp` | Meta verification: `hub.verify_token` must equal `WHATSAPP_VERIFY_TOKEN` |
| `POST /webhooks/whatsapp` | `X-Hub-Signature-256` HMAC is checked when `WHATSAPP_APP_SECRET` is set |
| `POST /webhooks/telegram` | `X-Telegram-Bot-Api-Secret-Token` is checked when `TELEGRAM_WEBHOOK_SECRET` is set |

## Tests

```bash
python -m pytest lead_desk/tests tests
```

The tests cover:

- The seed eval cases (`data/eval_cases.jsonl`).
- Exact parity with `src/scoring_engine.py` on all 180 synthetic leads in `rules-v1` mode.
- `rules-v1.1` agreeing with the synthetic family labels on all 180 leads.
- The email, WhatsApp and Telegram parsers.
- Filters and ranking.
- The guardrail.
- Notifier dry-run and the refusal to notify the customer.
- The approve/reject flow and webhook auth.

## Configuration (`.env`)

Copy the repo-root `.env.example` to `.env`. Every variable is optional.

| Variable | Used for |
| --- | --- |
| `LEAD_DESK_DB_PATH` | SQLite file for `ingest` / `imap-poll` / `serve-webhooks` / `review` / `leads` |
| `LEAD_DESK_TENANT_ID` | Tenant id stored on every row |
| `LEAD_DESK_SALES_LED` | `true` = rent enquiries are parked as COLD and no rentals are matched |
| `LEAD_DESK_MAX_MATCHES` | Listings per packet |
| `LEAD_DESK_NOTIFY_LIVE` | **Master switch.** Even with credentials, notifiers stay in dry-run unless this is `true` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `AGENT_EMAIL_TO` | Email notifier (STARTTLS). Sends the summary plus `packet.json` to the agent's inbox |
| `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_API_VERSION`, `AGENT_WHATSAPP_TO` | WhatsApp Cloud API text to the agent's own number. Meta only allows free text within 24 h of the agent messaging the business number; otherwise you need an approved template |
| `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET` | Inbound WhatsApp webhook verification and signature check |
| `TELEGRAM_BOT_TOKEN`, `AGENT_TELEGRAM_CHAT_ID` | Telegram `sendMessage` to the agent's own chat (the agent must `/start` the bot first) |
| `TELEGRAM_WEBHOOK_SECRET` | `secret_token` you pass to Telegram `setWebhook` |
| `IMAP_HOST`, `IMAP_PORT`, `IMAP_USER`, `IMAP_PASSWORD`, `IMAP_FOLDER` | Email intake (read-only: fetch UNSEEN) |
| `FEATURE_PARTNER_LISTINGS_API` | Off. Partner feeds are not built yet (Phase D) |
| `FEATURE_SCRAPE_LISTINGS` | Off. Scraping stays disabled until a ToS/legal review |

Safety rule in code: every notifier refuses to deliver if its recipient equals the lead's own contact handle (`CustomerRecipientError`).

## Layout

```
lead_desk/
  schema.py            Lead, LeadScore, Listing, SearchFilters, AgentPacket (Pydantic)
  intake/extract.py    PT/EN extraction: budget, timeline, city, typology, m², amenities, phone, listing ref
  intake/normalize.py  email | whatsapp | telegram -> Lead
  intake/webhooks.py   WhatsApp / Telegram webhook stub
  intake/imap_poll.py  IMAP poll or .eml folder
  scoring.py           deterministic HOT/WARM/COLD + rationale (rules-v1.1; rules-v1 = exact seed port)
  guardrail.py         banned-attribute check on rationale / next action / draft / notes
  property_match/      provider interface (mock / partner API / scrape, gated) + filter & rank
  packet.py            agent packet + draft reply (PT or EN)
  notifiers.py         AgentNotifier: CLI | Email | WhatsApp | Telegram (dry-run by default)
  hitl.py              approve / reject / reject-listing-and-rematch
  storage/             SQLite repository + schema_sqlite.sql + schema_postgres.sql
  data/                synthetic payloads, sample inbox, mock inventory
```

## Scoring: what changed vs the seed (`src/scoring_engine.py`)

`rules-v1.1` (default) keeps the seed points table and adds three things:

1. **The HOT gate from the written policy** (`n8n/prompts/lead_scoring_v1.md`): buy/sell intent, **and** (timeline ≤ 90 days or views ≥ 8 or saved ≥ 3), **and** contactable (phone or already replied). A lead that scores 70 or more but fails the gate is held at WARM, and the rationale says why.
2. **A few extra intent keywords** that the seed misses but `data/synthetic_leads.csv` uses: "selling", "listar o/a", "pôr à venda", "buying", "purchase".
3. **Whole-word guardrail matching**, so "terrace" no longer trips "race", plus the remaining policy categories (ethnicity, disability, sexual orientation, family status) and the language-ability / neighbourhood proxies.

`score_lead(lead, strict_policy=False)` reproduces the seed `rules-v1` exactly, and a test checks this.

Results on the 180 synthetic leads, measured against their `synthetic_family` label:

| Rules | Leads in the expected band |
| --- | --- |
| `rules-v1` (seed) | 148 / 180 |
| `rules-v1.1` | 180 / 180 |
