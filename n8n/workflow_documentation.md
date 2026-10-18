# n8n POC — lead scoring webhook

## What the automation does

A licensed agent (or a form) POSTs a JSON lead to `/webhook/lead-score`. n8n:

1. Builds the **versioned** system prompt from `n8n/prompts/lead_scoring_v1.md` (paste into an n8n env var `LEAD_SCORING_PROMPT`, or keep the file as source of truth).
2. Calls OpenAI Chat Completions with `temperature=0` and JSON mode.
3. Parses the model JSON. If parsing fails, **fail closed** to COLD + “human reviews”.
4. Returns the score to the caller. It does **not** send email or WhatsApp.

This is UC-1 only.

## Why it fits the use case

Chleo asked for transparency. The workflow has four visible steps, a frozen prompt file, and a structured payload an ops manager can read. That is easier to trust than “we put ChatGPT in WhatsApp.”

## How to run it

1. Import `n8n/workflow.json` into n8n Cloud or self-hosted n8n.
2. Create Header Auth credentials: `Authorization: Bearer <OPENAI_API_KEY>`.
3. Paste `lead_scoring_v1.md` into the environment variable `LEAD_SCORING_PROMPT`.
4. Activate the workflow. Copy the test webhook URL.
5. POST a body such as:

```json
{
  "lead_id": "eval_01",
  "channel": "website",
  "city": "Lisboa",
  "message": "Quero comprar T2 em Lisboa. Orçamento 380 mil. Posso visitar amanhã à tarde.",
  "budget_eur": 380000,
  "timeline_days": 21,
  "property_views_7d": 12,
  "saved_listings": 4,
  "replied_to_agent": true,
  "phone_provided": true,
  "email_provided": true
}
```

## Equivalent local POC (this repo always runs)

n8n credentials differ by student machine. The **graded “POC runs” path** in this repository is:

```powershell
python src\run_poc.py --input data\eval_cases.jsonl --output evaluation\poc_actuals.jsonl
```

That uses the same band policy (`src/scoring_engine.py`). Optional `--llm` uses the same prompt file as n8n.

## Limitations versus production

| POC | Production |
| --- | --- |
| One webhook, no queue | Idempotent queue, retries with jitter, circuit breaker (Week 5/10) |
| No CRM write-back | Write to the agency CRM with least-privilege credentials |
| No error workflow | n8n Error Trigger + alert “what/why/when/data/next” |
| Prompt in env var | Prompt registry + version logged on every score |
| OpenAI only | Provider fallback |
| No HITL UI | Round 2 Streamlit gate before any draft is “ready” |
| Student synthetic payloads | DPA, retention, access logs |

## Demo backup

If live n8n is down in the pitch: run `python src\run_poc.py` and show `evaluation/poc_actuals.jsonl` plus this diagram.

```text
POST /lead-score → Build prompt → OpenAI JSON → Fail-closed parse → JSON response
```
