# Agent instructions for this repository

## Product goal

Help a Portuguese SME estate-agency CEO (Chleo) **see** how a lead-scoring assistant would work: transparent bands, allowed features only, human final decision.

## Hard rules

- Do not invent live client names, emails, or phone numbers. Use the synthetic `lead_*` IDs in `data/`.
- Do not add auto-send integrations (Gmail/Twilio “send”). Draft + HITL only.
- Do not treat neighbourhood, nationality, or language ability as a proxy for creditworthiness or “quality of person”.
- Do not claim EU AI Act or GDPR **certification**. Document a first-pass with gaps and escalation.
- Round 1: no LangSmith project in the submission pack.
- Keep the MVP to **one** path: score → explain → draft → approve/reject.

## Preferred stack

- Shared logic: `src/scoring_engine.py` (Pydantic + deterministic rules; optional LLM).
- POC orchestration: n8n workflow in `n8n/workflow.json`.
- MVP: LangGraph in `mvp/graph.py`, UI in `mvp/app.py`.
- Charts: `charts/generate_charts.py` — one message per chart, CEO language.

## Definition of done (Round 1)

Research + 4–6 charts + running POC path + eval mini-set + cost/timeline + pitch outline + empty decision template.
