# Project requirements — Chleo Lead Agent (Round 1 + 2)

## Problem

Chleo’s SME agency in Portugal receives more portal and website enquiries than agents can work with the same quality. Hot buyers and motivated sellers wait; cold browsers consume call time. Chleo does not trust “the AI” because it is not obvious **what it does, who decides, and how success is measured**.

## In scope

- Research the Portuguese residential agency market at SME scale.
- Propose three AI use cases; POC and MVP **only** for lead qualification + next-action recommendation.
- Synthetic lead data and public market context (no live personal data).
- n8n (or equivalent Python) POC that returns structured scores.
- Round 1 evaluation plan with pass/fail criteria and ≥5 scored cases.
- Round 2: Streamlit + LangGraph MVP with **human-in-the-loop** before any outbound draft is marked ready.
- Consulting docs: ROI/risk, EU AI Act first-pass, GDPR, strategy with a 60-day pilot.

## Out of scope

- Auto-sending email/SMS/WhatsApp to consumers.
- Automated rejection of housing access or credit decisions.
- Scraping live Idealista/Imovirtual personal inboxes.
- Fine-tuning a model.
- Interactive BI dashboard in Round 1 (optional stretch only after required files exist).
- LangSmith submission in Round 1.

## Functional requirements

| ID | Requirement | Acceptance |
| --- | --- | --- |
| FR-1 | Score a lead as HOT / WARM / COLD | JSON field `band` is one of those three |
| FR-2 | State buyer vs seller vs rent vs unknown intent | `intent` populated |
| FR-3 | Explain the score in plain language | `rationale` cites only allowed signals |
| FR-4 | Suggest a next action for the **agent** | `next_action` is operational, not “be nicer” |
| FR-5 | Never use nationality, race, gender, religion, or family status | Guardrail fail if rationale mentions banned attributes |
| FR-6 | Agent must approve before a draft is “ready to send” | MVP HITL gate; POC does not send |
| FR-7 | Someone else can run the repo from README | venv + requirements + .env.example |

## Non-functional

- Pin dependencies; secrets in `.env`.
- Version prompts in files, not only in n8n node UIs.
- Fail loud if required env vars are missing when `--llm` is used.
- Prefer a small model (`gpt-4o-mini`) for cost and energy (SCI: R = one lead scored).

## Prompt log

| Version | File | Change |
| --- | --- | --- |
| v1 | `n8n/prompts/lead_scoring_v1.md` | Initial structured scorer for Round 1 POC |
| v1-mvp | `mvp/prompts/qualify_and_draft_v1.md` | Adds Portuguese draft + HITL reminder |

## Changelog

| Date | Change |
| --- | --- |
| 2026-09-17 | Scaffold Round 1 pack and Round 2 MVP skeleton for Ironhack capstone |
