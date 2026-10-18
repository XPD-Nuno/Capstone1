# GDPR / RGPD documentation — first-pass

Navigator memo. CNPD and independent counsel own the binding view. Student project uses **synthetic** leads only.

## Processing in production (intended)

| Item | Description |
| --- | --- |
| Purposes | Prioritise follow-up of people who asked the agency about buying/selling/renting |
| Data | Message text, optional name/phone/email, city of interest, channel, behavioural counts (views, saves), score, rationale, agent override |
| Data subjects | Enquirers (customers / prospects) |
| Special categories | **Not sought**. If a message contains health/religion/etc., do not use it in the score (policy already bans it) |

## Lawful basis (production)

| Processing | Basis (working) | Notes |
| --- | --- | --- |
| Responding to an enquiry they sent | **Contract steps** (Art. 6(1)(b)) or **legitimate interests** (Art. 6(1)(f)) in pre-contract | Do not stretch 6(1)(b) to long drip campaigns |
| Scoring / profiling to order the call list | **Legitimate interests** with balancing test | Not “we already have the data so we can profile” |
| Marketing drips to COLD leads | Often **consent** or ePrivacy rules for electronic mail | Out of MVP scope on purpose |
| Model **training** on CRM text | **Not permitted** by default | Separate basis, DPIA, maybe never |

ePrivacy can beat legitimate interests for tracking and some electronic comms. Portal pixels are a different conversation.

## Data flow (pilot architecture)

```text
Form / CSV  →  Lead desk (agency VPC or laptop)  →  optional OpenAI API (US/other)
            →  logs (score, version, actor)     →  LangSmith sample traces (optional)
```

**Transfers:** OpenAI and LangSmith are typically **third countries**. Use **SCCs** + transfer assessment; do not pretend “the model is in Lisbon” if it is not. Alternative: EU-hosted model later.

## Retention

Proposal: operational scores **12 months**; raw message text **90 days** unless a transaction file needs it; LangSmith traces **sampled and time-boxed**. Delete on request unless another basis applies (AML file, dispute).

## Data-subject rights

| Right | How the MVP design helps |
| --- | --- |
| Access | Export the stored JSON for `lead_id` |
| Rectification | Agent edits CRM; re-score |
| Erasure | Delete row + trace ids; note subprocessors |
| Objection to profiling | Honour by routing to **manual-only** queue |
| Human review of significant decisions | Scores must not be the sole basis to refuse a viewing |

## Short DPIA (pilot)

| Topic | Note |
| --- | --- |
| Necessity | Agents already read the same messages; scoring automates order, not a new data source |
| Proportionality | No special-category targeting; COLD is park not blacklist |
| Risks to people | Unfair de-prioritisation, distress from aggressive follow-up, leakage via US APIs |
| Measures | HITL, banned attributes, minimisation, SCCs, no auto-send, synthetic in this repo |
| Residual | Medium until a DPA with the LLM vendor is signed |

DPIA **full** version is required if Chleo concludes high risk to rights. This student short form is a starter, not that conclusion.

## Processors (illustrative)

| Processor | Task | Need |
| --- | --- | --- |
| Cloud LLM provider | Optional draft / optional LLM score | DPA + SCCs |
| LangSmith | Eval traces | DPA; no extra special category |
| n8n Cloud | Orchestration | DPA; prefer self-host if Chleo is strict |

## Student-project statement

`data/synthetic_leads.csv` is fake. Do not load real client exports into this GitHub repo or into a personal LangSmith account without a DPA and minimisation.
