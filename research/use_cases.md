# Use cases for Chleo’s SME agency

All three fit a 10–50 person Portuguese residential agency. Only **UC-1** is built as the Round 1 POC and Round 2 MVP.

## UC-1 — Lead qualification and next-action scoring (primary)

**Job to be done:** When an enquiry arrives, tell the duty agent whether to call in the next hour, qualify this week, or park.

**Inputs:** message text, optional budget, optional timeline, recent listing views, saved listings, whether a phone number exists, channel, city.

**Outputs:** intent (`buy` / `sell` / `rent` / `unknown`), band (`HOT` / `WARM` / `COLD`), 0–100 score, rationale, next action for the **human**.

**Why this size of company:** eight to twenty agents cannot work 40+ portal leads/day at the same quality. They already triage mentally; this makes the triage inspectable for Chleo.

**Success criteria (pilot):**

- ≥90% of HOT labels agree with a senior agent on a 30-lead weekly sample (HITL).
- Median time-to-first-touch for HOT leads falls (target: under 60 minutes during office hours).
- Zero production messages sent without agent approval.

**Out of scope:** auto-email, credit checks, automated valuation.

## UC-2 — Enquiry reply drafting with human approval

**Job to be done:** Draft a Portuguese (or English) reply in the agency’s tone; the agent edits and sends.

**Why it fits later:** it reuses UC-1 context (band + intent) so HOT leads get a viewing offer and COLD leads get a short, non-pushy note.

**Why it is not the POC:** it is easy to demo and easy to over-claim. Without scoring, Chleo still does not know *who* to reply to first.

**Main risk:** hallucinated availability (“the T2 in Campo de Ourique is still free”). Drafts must not invent stock.

## UC-3 — Weekly market briefing for agents

**Job to be done:** Monday morning one-pager: INE price and transaction moves for the offices’ cities, plus three talking points.

**Why it fits:** SME agents lose listings when they sound less informed than network brands with research desks.

**Why it is the risk contrast:** low personal-data risk, high hallucination risk if the model is allowed to invent €/m². Good teaching case for “AI that must cite.”

**Not built in Round 1** so the demo stays one capability.

## Why not other popular real-estate AI ideas

| Idea | Verdict for this SME |
| --- | --- |
| Public chatbot that negotiates | Transparency and hallucination risk too high for Round 1 |
| Computer vision on listing photos | Nice-to-have; does not fix speed-to-lead |
| Full autonomous nurture agent | ePrivacy + brand risk; contradicts HITL story Chleo needs |
