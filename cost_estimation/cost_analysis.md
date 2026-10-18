# Cost analysis — 60-day pilot for Chleo

Figures are **planning numbers** for a consulting conversation, not a binding quote. Currency EUR. VAT extra where applicable.

## What we are costing

A 60-day **pilot of UC-1** on one office (duty agent + operations manager), synthetic-to-CRM path in production would add DPA work not fully priced here.

## One-off (pilot)

| Item | Low | Base | High | Notes |
| --- | --- | --- | --- | --- |
| Discovery + CRM field mapping | 1,200 | 2,000 | 3,500 | 3–5 workshops |
| n8n workflow + prompt + fail-closed parse | 800 | 1,500 | 2,500 | Reuses this POC |
| HITL UI (Streamlit/FastAPI) | 1,500 | 3,000 | 5,000 | Round 2 MVP hardening |
| Evaluation set + LangSmith project | 600 | 1,200 | 2,000 | 30–50 golden cases with a senior agent |
| GDPR / AI Act first-pass pack | 800 | 1,500 | 3,000 | Consultant, **not** law firm opinion |
| Training two champions | 400 | 800 | 1,200 | |
| **Total one-off** | **5,300** | **10,000** | **17,200** | |

## Monthly run (pilot volume: ~800 scored leads)

| Item | Base | Notes |
| --- | --- | --- |
| LLM (`gpt-4o-mini`, ~800 tokens in+out / lead) | ~15–40 | Cache identical payloads |
| n8n Cloud starter / self-host electricity | 24–60 | Self-host may be cheaper at this volume |
| LangSmith developer | 0–39 | Traces on sample, not 100% if cost-capped |
| Consultant retain (4h/month) | 400 | Prompt fixes, eval review |
| **Total monthly** | **~450–550** | Dominated by people, not tokens |

## Value sketch (order of magnitude)

If the delay chart’s **direction** is right — not its exact euros — recovering **one extra completed instruction per quarter** at €10–15k commission already covers the base pilot. That is the ask: *measure* this, do not believe the synthetic chart.

## Cost of *not* piloting

Agents keep pasting client messages into consumer ChatGPT (uncontrolled subprocessors, no logs). That is already a RGPD incident waiting to happen.

## Green / SCI note

Functional unit **R** = one lead scored. Prefer mini model, short prompt, cache. Offsets are not used to “green” the number (Week 16).
