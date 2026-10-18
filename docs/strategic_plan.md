# Strategic plan — POC → pilot → deploy → commercialise

## Narrative

Round 1 is a **sales conversation** with Chleo. Round 2 is a **leave-behind** plus a tool a duty agent can click. Full rollout is a **different project**.

## Phase 0 — POC (bootcamp / this repo)

Done when: webhook or `run_poc.py` scores the golden set; charts tell the capacity story; paper eval exists.

## Phase 1 — 60-day pilot (one office)

**Success criteria (all required):**

1. ≥90% senior-agent agreement on HOT for a 30-lead weekly sample, two consecutive weeks  
2. Median HOT first-touch < 60 minutes in published office hours  
3. Zero auto-sends  
4. Zero confirmed banned-attribute rationales in the audit sample  
5. Champion still willing to run the Monday review without the consultant in the room  

**Kill / pivot if:** agreement <70% after week 4; agents refuse the UI; counsel says Annex III high-risk under Chleo’s actual workflow.

## Phase 2 — Deploy (offices 2–5)

Only after Phase 1. CRM write-back, SSO, retention jobs, DPA signed, EU-region model if transfer risk is unacceptable. UC-2 drafts with the same HITL.

## Phase 3 — Commercialise (optional)

Chleo is an **agency**, not a proptech. Default commercialisation is **internal efficiency**, not a SaaS spin-out. If they later sell the desk to a network, **provider** obligations under the AI Act jump — see the EU memo.

Go-to-market for **us as consultants:** productised 60-day pilot for other SME agencies (same pack, new golden set). Pricing: €8–12k pilot, not outcome-based until we have two measured pilots.

## KPIs

| KPI | Owner | Cadence |
| --- | --- | --- |
| HOT agreement rate | Ops champion | Weekly |
| Time-to-touch HOT | CRM | Weekly |
| Tokens / lead (SCI R) | Ops | Monthly |
| Override rate | Ops | Weekly |
| Incidents (wrong call, complaint) | Chleo | Immediate |

## Green software

R = one lead scored. Levers: mini model, cache, rules engine first (often **zero** GPU), short prompts. Do not buy offsets to decorate the slide.
