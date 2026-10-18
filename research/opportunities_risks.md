# Opportunities and risks — SME Portuguese estate agency

Mapped for Chleo (10–50 people, 2–5 offices). Scores are consultant judgement, not a quantified model.

## Opportunity map

| Opportunity | Why it fits this company size | Value hypothesis | Dependency |
| --- | --- | --- | --- |
| Lead qualification / next-action scoring | Uses data the agency already captures in forms; no data-science hire | Faster contact of HOT buyers/sellers; fewer wasted calls on browsers | Clean-enough CRM fields; agent trust |
| HITL reply drafting (PT/EN) | Juniors already draft WhatsApp; seniors edit | Minutes saved per enquiry; more consistent tone | Human send; template library |
| Weekly market briefing from public stats | INE and listings are public; SME cannot afford a research desk | Agents sound current in Lisboa vs Porto vs Algarve conversations | Must cite sources; no fake “AI valuation” |
| Listing photo / description assist | Stretch | Faster time-to-portal | Brand voice; advertising law |
| Valuation AVM | Poor fit now | Clients will treat a number as a promise | High complaint and professional-liability risk |

**Priority for Round 1 POC:** opportunity 1. It is the only one that directly answers “where should my eight agents spend Tuesday morning?”

## Risk map

| Risk | Type | Likelihood if naive build | Impact | Mitigation in this design |
| --- | --- | --- | --- | --- |
| Profiling of identifiable people (messages, phones, emails) | GDPR / RGPD | High | High — CNPD complaint, trust loss | Synthetic data in the student project; production: minimisation, retention, DPIA, lawful basis |
| Automated decision that “this person is not worth housing help” | GDPR Art. 22 + ethics | Medium if scores auto-route to /dev/null | High | HITL; COLD means *park*, never *reject housing* |
| Discriminatory scoring (nationality, neighbourhood as poverty proxy) | Ethics / AI Act Art. 5 adjacent | Medium if prompts are sloppy | High — reputational and legal | Banned-attribute list; eval cases; rationale audit |
| Hallucinated “market value” in a briefing | Professional liability | High if RAG-less LLM | High | Use case 3 must quote INE, not invent €/m² |
| Portal T&Cs / scraping | Contract / unfair competition | High if someone “connects Idealista inbox” | High | Manual/CSV/webhook intake only |
| Shadow IT: ChatGPT with real client pastes | Security | Already happening in SMEs | High | Give a contained tool so people stop pasting CRM into consumer ChatGPT |
| Over-automation of nurture sequences | Commercial + ePrivacy | Medium | Medium | No auto-send in MVP |
| Energy / cost surprise | Green + finance | Low at this volume | Low | Small model, cache identical payloads, R = 1 lead scored |
| “The AI said they were cold” used in a dispute | Operational | Medium | Medium | Log the rationale; agent override is the record |

## Risk vs opportunity (for the chart)

| Use case | Opportunity (1–5) | Risk if poorly governed (1–5) |
| --- | --- | --- |
| Lead scoring + next action | 5 | 4 (manageable with HITL) |
| Approved reply drafting | 4 | 3 |
| Weekly INE market briefing | 3 | 2 |
| Automated valuation | 2 | 5 — out of scope |

## What we will explicitly **not** do

- Score people on protected attributes or “foreign vs local” quality.
- Auto-decline viewings.
- Claim the tool is EU AI Act certified or CNPD-approved.
- Train on Chleo’s real CRM during this student project.
