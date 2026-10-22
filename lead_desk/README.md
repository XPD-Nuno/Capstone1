# Lead Desk — vertical slice

One path, end to end: **inbound message → normalize → score (HOT/WARM/COLD + why) → match properties → agent packet on the desk (web dashboard or CLI) → agent approves or rejects**.

- **Nothing is sent to anyone.** The desk (web dashboard or CLI) is the only delivery channel. The agent copies the approved draft and sends it from their own email, phone or CRM. Outbound agent notifications (email, Telegram, ...) are deferred until the MVP has been tested on real situations; the `AgentNotifier` interface stays so they can return.
- **Intake channels:** email (portal notifications and direct email, via IMAP or `.eml` files) and Telegram. WhatsApp is deferred until after real MVP tests.
- **Scoring** uses operational signals only (intent, budget, timing, search activity, contactability). Nationality, neighbourhood and language ability are never inputs, and a guardrail blocks any system text that mentions a banned attribute.
- **Listings:** Idealista Search API when credentials are set, otherwise a synthetic mock inventory.
- All demo data is synthetic: `lead_*` ids, `@example.invalid` addresses, placeholder Telegram ids, `mock_lst_*` listings.
- This is a first-pass build. It does not certify anything under GDPR or the EU AI Act.

## Run the web dashboard

```bash
pip install -r lead_desk/requirements.txt
npm --prefix web install && npm --prefix web run build
python -m lead_desk serve-api --seed-demo     # http://127.0.0.1:8000
```

The FastAPI backend (`lead_desk/api/app.py`) wraps the same `LeadDesk` pipeline and `hitl` functions as the CLI, and serves the built React app from `web/dist`. The dashboard has:

- **Lead queue:** counts for needs-review / HOT / WARM / COLD (click to filter), search across lead id, city, message, typology and listings, status / channel / sort filters (kept in the URL), a table on desktop and cards on mobile.
- **Lead detail:** score and band with the reasons behind them, the customer message and logistics notes, property matches, the draft reply with a copy button, and the decision history.
- **Decisions:** approve, reject the whole packet (two clicks), or tick "Not a fit" on listings to exclude them and re-match. Decisions are signed with an agent id kept in the browser.

Nothing is sent from the dashboard. Approving marks the packet; the agent copies the draft and sends it themselves. There is no login, so `serve-api` binds to `127.0.0.1` by default; put it behind an authenticating proxy before exposing it. `--db lead_desk.sqlite3` keeps data between runs (the default is in-memory).

Frontend development with hot reload (the Vite dev server proxies `/api` to port 8000, or to `LEAD_DESK_API`):

```bash
python -m lead_desk serve-api --seed-demo      # terminal 1
npm --prefix web run dev                       # terminal 2 -> http://localhost:5173
```

| Endpoint | What it does |
| --- | --- |
| `GET /api/stats` | Counts by band and status, and the active listings provider |
| `GET /api/leads?band=&status=&channel=&q=&sort=priority\|newest\|score` | Current packet per lead, filtered and sorted |
| `GET /api/leads/{lead_id}` | Current packet, decision, excluded listings, packet history, events |
| `POST /api/packets/{id}/approve` | `{agent_id, note}`; 409 if already decided or blocked by the guardrail |
| `POST /api/packets/{id}/reject` | `{agent_id, note, listing_ids}`; with `listing_ids` the lead is re-matched without them |
| `POST /api/intake/{email\|telegram}` | `{payload, lead_id?, signals?}`: run one inbound message through the pipeline |
| `POST /api/demo/load` | Load the synthetic demo leads that are not already on the desk |
| `GET /api/leads/{lead_id}/export`, `DELETE /api/leads/{lead_id}`, `POST /api/retention/purge` | Export, erase, retention purge (see "Data requests and retention") |

Interactive API docs are at `/docs`.

## Run the CLI demo

```bash
pip install -r lead_desk/requirements.txt
python -m lead_desk demo
```

The demo reads `lead_desk/data/synthetic_payloads.json`: 7 payloads made of an Idealista-style email, direct emails and Telegram updates. For each one it prints the agent packet and asks:

```
[a]pprove | [r]eject | r <listing_id ...> reject listings & re-match | [s]kip
```

- `a`: marks the packet as approved to present. Nothing is sent to anyone.
- `r`: rejects the packet. The lead is kept; only the listings are not presented.
- `r mock_lst_001`: excludes that listing for this lead (stored in `rejected_listings`) and re-matches.
- `s` / end of input: leaves the packet as `pending_review`.

Useful flags:

| Command | What it does |
| --- | --- |
| `python -m lead_desk demo --json` | Also prints the full packet JSON |
| `python -m lead_desk demo --no-review` | No prompts (CI / screenshots) |
| `printf 'a\nr\ns\n' \| python -m lead_desk demo` | Scripted decisions |
| `python -m lead_desk demo --db lead_desk.sqlite3` | Keep the database (the default is in-memory) |

## Other commands

```bash
python -m lead_desk imap-poll --db lead_desk.sqlite3           # IMAP if configured, else data/sample_inbox/*.eml
python -m lead_desk ingest --channel telegram --file update.json --db lead_desk.sqlite3
python -m lead_desk serve-api --db lead_desk.sqlite3           # web dashboard + JSON API on :8000
python -m lead_desk serve-webhooks --db lead_desk.sqlite3      # Telegram webhook stub on :8787
python -m lead_desk review --db lead_desk.sqlite3              # approve/reject everything pending
python -m lead_desk leads --db lead_desk.sqlite3 --band HOT
python -m lead_desk export-lead lead_9001 --db lead_desk.sqlite3   # see "Data requests and retention"
python -m lead_desk delete-lead lead_9001 --db lead_desk.sqlite3
python -m lead_desk purge --days 365 --dry-run --db lead_desk.sqlite3
```

The webhook endpoint is `POST /webhooks/telegram`. It checks `X-Telegram-Bot-Api-Secret-Token` when `TELEGRAM_WEBHOOK_SECRET` is set. The server is a stdlib demo stub; put it behind HTTPS before pointing Telegram at it.

## Scoring rules (`rules-v1.2`)

| Band | When | Next action |
| --- | --- | --- |
| HOT | Buy/sell intent, score ≥ 70, (timeline ≤ 90 days or views ≥ 8 or saved ≥ 3), and a phone number or a previous reply | Call within 60 minutes |
| WARM | Real interest that misses the HOT gate | Qualifying question, call this week |
| WARM | Genuine rental intent. Never HOT, because of the lower commission | Lettings qualifying question, after HOT sales leads |
| COLD | Email-only leads: reachable, but no phone number and no previous reply | Reply by email with one question and ask for a phone number. Do not phone |
| COLD | Spam, browsing, or unclear intent with a low score | Low-frequency drip |

These criteria will be revisited once Lead Desk runs on real situations.

The bands and points come from the seed engine `src/scoring_engine.py`. `score_lead(lead, strict_policy=False)` still reproduces the seed `rules-v1` exactly, and a test checks this on all 180 synthetic leads. The differences from the seed are:

1. The HOT gate from the written policy (`n8n/prompts/lead_scoring_v1.md`).
2. The client decisions above on email-only leads and rentals.
3. A few extra intent keywords that the synthetic data uses: "selling", "listar o/a", "pôr à venda", "buying", "purchase".
4. Whole-word guardrail matching, so "terrace" no longer trips "race", plus the policy categories missing from the seed list.

The full list of differences, and why eval_03 moves from WARM to COLD, is in [scoring_versions.md](scoring_versions.md).

## Data requests and retention (first pass)

Lead Desk stores each lead's message, extracted fields, scores, packets, agent decisions and an event log. Three tools help answer a data-subject request or apply a retention period:

| Need | CLI | API |
| --- | --- | --- |
| Give a lead a copy of their data | `python -m lead_desk export-lead lead_9001 --db lead_desk.sqlite3 [--out lead_9001.json]` | `GET /api/leads/{lead_id}/export` (JSON download) |
| Erase a lead | `python -m lead_desk delete-lead lead_9001 --db lead_desk.sqlite3 [--yes] --agent agent_ana` | `DELETE /api/leads/{lead_id}?agent_id=agent_ana` |
| Erase leads with no activity for N days | `python -m lead_desk purge --db lead_desk.sqlite3 --days 365 [--dry-run]` | `POST /api/retention/purge?days=365&dry_run=true` |

- **Export** returns the lead record, every packet (with matches, draft and decision), excluded listings and the event history.
- **Erase** removes the lead, its packets, decisions, events and excluded listings in one transaction. It keeps one line in `erasure_log` with a SHA-256 of the lead id, who erased it, why (`request` or `retention`) and row counts, so the agency can later show that the erasure happened without keeping the data. SQLite `secure_delete` is on, so erased text is overwritten in the database file. If the same person writes again, they come back as a new lead with no history.
- **Retention:** a lead's last activity is its latest contact, score, packet or decision. `purge` uses `--days`, or `LEAD_DESK_RETENTION_DAYS` when set; with neither, it refuses to run. Nothing runs on a schedule: run it from cron (or a scheduled job) once a period is agreed. Always try `--dry-run` first.

This is a first pass. It does not make Lead Desk GDPR-compliant on its own, and the following gaps remain:

- No identity check: whoever runs the command or calls the API can export or erase any lead. The API has no login, so keep it on localhost.
- Requests are found by `lead_id` only. Finding a person's leads by email address or Telegram id is not built yet.
- Copies outside the database are not touched: backups, exported JSON files, copied drafts, server logs, the original mailbox and Telegram chat.
- No retention period has been chosen. That is a decision for the agency (with its DPO or legal adviser), not a code default.
- No record of processing activities, consent capture, objection (opt-out of scoring) or rectification flow. Correcting data today means re-ingesting it.
- The Postgres schema has the `erasure_log` table but no Postgres repository yet, so these tools are SQLite-only.
- The dashboard does not show export or erase buttons yet; use the CLI or the API.

## Listings: Idealista first

- **`IdealistaProvider`** calls the Idealista Search API v3.5: an OAuth2 client-credentials token, then `POST /3.5/pt/search`. The search uses the city centre plus a radius, and passes operation, price, size, bedrooms and the amenity flags (lift, garage, terrace, pool, A/C, storage room). Results become `idealista_<propertyCode>` listings.
- **Idealista API access requires partner approval from Idealista.** Apply for API keys before expecting real listings. The free tier has a small monthly request quota; every search is counted in `usage_meters.listing_fetches`.
- **Fallback:** with no `IDEALISTA_API_KEY` / `IDEALISTA_API_SECRET`, the mock inventory is used. If an Idealista call fails (network, quota), the desk warns on stderr and falls back to the mock inventory for that search. Each match line shows its source (`[idealista]` or `[mock]`).
- **Scraping** stays disabled (`FEATURE_SCRAPE_LISTINGS=false`) until a ToS/legal review.

## Tests

```bash
python -m pytest lead_desk/tests tests
npm --prefix web test            # Vitest: formatting, URL filters, queue and detail pages
npm --prefix web run typecheck
npm --prefix web run build && npm --prefix web run e2e   # Playwright smoke test (first time: npx --prefix web playwright install chromium)
```

The Playwright smoke test (`web/e2e/smoke.spec.ts`) starts `python -m lead_desk serve-api --seed-demo` on a fresh in-memory database and drives Chromium through two flows: queue → lead_9001 → exclude a listing and re-match → approve; and lead_9002 → two-step reject → back to the queue with the updated statuses. Set `PYTHON` if your interpreter is not `python3`.

GitHub Actions (`.github/workflows/ci.yml`) runs three jobs on every pull request and on pushes to `main`: the Python tests, the web typecheck + Vitest + build, and the Playwright smoke test.

The Python tests cover:

- The seed eval cases. `eval_03` is expected COLD under `rules-v1.2` because it is email-only.
- Exact `rules-v1` parity with the Round 1 engine.
- `rules-v1.2` against the synthetic family labels, adjusted for the email-only and rental decisions.
- The email and Telegram parsers.
- Filters and ranking.
- Idealista request building and mapping, using a fake HTTP transport (no real API call).
- Fallback to the mock inventory.
- The guardrail.
- The CLI-only delivery.
- The approve/reject flow and Telegram webhook auth.
- The dashboard API: filters, search, sort, approve/reject conflicts, reject-listing re-match, intake and demo loading.
- Export, erasure (including that erased text is gone from the database file) and retention purge, via the repository, API and CLI.

The frontend tests use `web/src/test/fixtures.json`, a snapshot of real API responses for the synthetic demo leads.

## Configuration (`.env`)

Copy the repo-root `.env.example` to `.env`. Every variable is optional.

| Variable | Used for |
| --- | --- |
| `LEAD_DESK_DB_PATH` | SQLite file for `ingest` / `imap-poll` / `serve-webhooks` / `review` / `leads` |
| `LEAD_DESK_TENANT_ID` | Tenant id stored on every row |
| `LEAD_DESK_MAX_MATCHES` | Listings per packet |
| `LEAD_DESK_RETENTION_DAYS` | Default period for `purge` / `POST /api/retention/purge`. Unset means no default |
| `TELEGRAM_WEBHOOK_SECRET` | The `secret_token` you pass to Telegram `setWebhook` |
| `IMAP_HOST`, `IMAP_PORT`, `IMAP_USER`, `IMAP_PASSWORD`, `IMAP_FOLDER` | Email intake (read-only: fetch UNSEEN) |
| `IDEALISTA_API_KEY`, `IDEALISTA_API_SECRET` | Idealista Search API credentials (partner approval required). Unset means the mock inventory |
| `IDEALISTA_COUNTRY`, `IDEALISTA_MAX_ITEMS`, `IDEALISTA_DEFAULT_RADIUS_KM` | Search country (`pt`), results per search (max 50), and radius around the lead's city |
| `FEATURE_SCRAPE_LISTINGS` | Off |

## Layout

```
lead_desk/
  schema.py            Lead, LeadScore, Listing, SearchFilters, AgentPacket (Pydantic)
  intake/extract.py    PT/EN extraction: budget, timeline, city, typology, m², amenities, phone, listing ref
  intake/normalize.py  email | telegram -> Lead
  intake/webhooks.py   Telegram webhook stub
  intake/imap_poll.py  IMAP poll or .eml folder
  scoring.py           deterministic HOT/WARM/COLD + rationale (rules-v1.2; rules-v1 = exact seed port)
  guardrail.py         banned-attribute check on rationale / next action / draft / notes
  property_match/      providers (Idealista, mock, scrape gated) + filter & rank
  packet.py            agent packet + draft reply (PT or EN)
  notifiers.py         AgentNotifier interface + CLINotifier (the only delivery for now)
  hitl.py              approve / reject / reject-listing-and-rematch
  api/app.py           FastAPI backend for the dashboard (serves web/dist)
  storage/             SQLite repository + schema_sqlite.sql + schema_postgres.sql
  data/                synthetic payloads, sample inbox, mock inventory
web/                   React + Vite + Tailwind dashboard
  src/pages/           QueuePage (lead queue), LeadDetailPage (detail + decisions)
  src/components/      badges, score ring, listing card, layout, toasts
  src/api.ts           typed client for /api
```
