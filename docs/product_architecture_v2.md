# Product architecture v2 — seven locked decisions

Pitch companion to [`charts/capstone1_product_workflow.html`](../charts/capstone1_product_workflow.html). **MODIFY** vs Idealista’s auto-WhatsApp qualifier: compete on transparent rules, human final decision, agent-owned lead history, and prepaid LLM quotas — not auto-messaging consumers.

Hard rules ([`AGENTS.md`](../AGENTS.md)): draft + HITL only; synthetic `lead_*` IDs in demos; no nationality / neighbourhood / language ability as creditworthiness proxies; no EU AI Act or GDPR certification claims.

---

## 1. Channel intake priority

| Priority | Channel | Why |
| --- | --- | --- |
| 1 | Email / portal notification parse | Idealista/Imovirtual often deliver enquiries as email; reliable without partner API |
| 2 | Official portal lead API / webhook | Structured JSON when partner plans exist |
| 3 | WhatsApp Business Cloud API | Dominant for PT agent outbound follow-up; inbound if they publish a business number |
| 4 | Website form / Meta lead ads webhook | Common SME sources |
| Deprioritize | Telegram | Weak in PT residential day-to-day |

**Rule:** app drafts only; agent sends from their own WhatsApp / email / CRM.

---

## 2. Lead repository

Tenant-scoped store (not session state):

- **Demo:** SQLite → **SaaS:** Postgres
- Tables: `tenants`, `users`, `leads`, `lead_events` (score versions, overrides, draft status), `usage_meters`
- UI: list / filter / open any past lead (band, source, last action, draft)
- Dedup: phone/email + portal listing ref when present

---

## 3. HOT / WARM / COLD (complete + gaps)

**In** `src/scoring_engine.py` today: intent, budget, timeline, views/saves, contactability, browsing/spam penalties; **HOT** if ≥70 and buy/sell; **COLD** if spam or &lt;35; else **WARM**; rent forced COLD for sales-led SME.

**Add later as operational signals only:** financing readiness, typology fit + price consistency, listing ref attached, repeat contact / SLA breach, source-quality weight (logistics, documented).

**Never use:** nationality, neighbourhood-as-person-quality, language ability.

---

## 4. Property search filters

Assistive match for scored buyer leads (not person scoring): operation, geo (district / concelho / freguesia / radius), typology T0–T5+, rooms, m², price / condo max, condition, energy class, amenities, exclude rejected listing IDs.

---

## 5. Property data tool ladder

1. Idealista Search / partner APIs  
2. Imovirtual / Casa Sapo partner feeds  
3. Agent MLS / CRM export  
4. Public-page extract only after ToS/legal review (commercial Phase 3 — not Round 1/2)

Scraping portal **inboxes** stays out of Capstone scope. Free tooling reference if extract is ever approved: Crawl4AI, Firecrawl, Scrapy, Playwright, Crawlee, ScrapeGraphAI.

---

## 6–7. API cost control + central admin

```
Agent app → API gateway → Tenant quotas
                         → Rules scorer (free)
                         → LLM drafts (billed)
                         → Listing fetch budget
Gateway ←→ Central admin (suspend / throttle / rotate keys)
```

- Rules-first scoring; LLM only when credits remain  
- Per-tenant caps: `scores`, `llm_tokens`, `listing_fetches`  
- Soft stop 80% / hard stop 100%; cache identical payloads; default mini model  
- Org API key + per-user login; disable user or tenant  
- Dashboard: cost per lead, cost per approved draft  

---

## Phased shape (keep Capstone MVP path)

| Phase | What |
| --- | --- |
| A | This blueprint + workflow HTML |
| B | Lead repository + history UI |
| C | Email + WhatsApp inbound capture + draft HITL |
| D | Property match filters + partner/API listings |
| E | Multi-tenant gateway + quotas |

**MVP lane unchanged:** score → explain → draft → approve/reject. Do not auto-send.
