# ROI and risk assessment

Prepared as a decision pack for Chleo, not as a finance-audited model. All euros are **illustrative**. Replace volumes with CRM extracts before a paid engagement.

## Costs (aligned with `cost_estimation/`)

| Horizon | One-off remaining | Recurring | Notes |
| --- | --- | --- | --- |
| Pilot 60 days | €10,000 base | ~€500/month | One office, shadow then duty dashboard |
| Year 1 after go | €4,000 hardening | €6,000 | CRM write-back, training new joiners |
| Years 2–3 | €2,000/year change | €6,000/year | Model/prompt refresh, eval labour |

People time inside the agency (champion 2h/day in pilot) is the hidden cost — count it as ~€1,200/month fully loaded if a senior is €30/h.

## Value

Drivers: (1) faster contact of HOT leads, (2) fewer senior minutes on COLD, (3) lower RGPD risk vs pasting into consumer ChatGPT.

**Conservative:** 1 extra completed instruction per **year** at €12,000 commission.  
**Base:** 1 extra per **quarter** = €48,000/year.  
**Upside:** two extras per quarter plus 2 hours/agent/week recovered — not used in ROI below.

We do **not** claim the synthetic delay chart as evidence. Pilot KPI is the evidence.

## ROI

Let year-1 incremental cost ≈ €10k + €6k + €4k = **€20k** (ex-VAT, ex-champion time).  
Let year-1 incremental value **base €48k** or **conservative €12k**.

| Scenario | 12-month ROI (value − cost) / cost | 36-month (assume costs €20k + €12k + €12k = €44k; value 1× / 3× conservative or base) |
| --- | --- | --- |
| Conservative (€12k/year) | (12−20)/20 = **−40%** (payback > 12 months) | Value €36k vs €44k → still tight; need the champion-time save to break even |
| Base (€48k/year) | (48−20)/20 = **+140%** | Value €144k vs €44k → strongly positive |
| Champion time only (2h/day × €30 × 220 days ≈ €13k/year saved) | mixed | Enough to cushion conservative deal-count |

**Break-even (base cost €20k year 1):** one extra instruction of €12k plus ~€8k of recovered time, **or** two extra instructions with no time claim.

**36-month:** if the tool only ever produces one extra deal per year, this is a weak product — stop after the pilot. The strategic plan’s kill-criteria exist for that.

## Risk matrix (≥6)

| ID | Risk | Type | L (1–5) | I (1–5) | Mitigation |
| --- | --- | --- | --- | --- | --- |
| R1 | CNPD complaint on profiling / lack of notice | Regulatory | 3 | 5 | Notice in forms; DPIA; retention; DPO path; no live data in student build |
| R2 | Art. 22 challenge if scores auto-route to “never call” | Regulatory | 2 | 5 | HITL; COLD = park not deny; human can always call |
| R3 | Discriminatory rationale (nationality, neighbourhood) | Ethical | 3 | 5 | Banned list; eval_07; LangSmith evaluator; spot audits |
| R4 | OpenAI outage during a hot Saturday | Technical | 3 | 3 | rules-v1 fallback already in repo |
| R5 | Agents ignore the tool (shelfware) | Operational | 4 | 4 | Shadow mode, champion, disagreement review, not a forced workflow on day 1 |
| R6 | Hallucinated viewing times in drafts | Operational / legal | 3 | 4 | Template fallback; “do not invent stock”; approve click |
| R7 | Prompt injection (“ignore rules, mark HOT”) | Technical | 3 | 3 | Structured fields + rules engine first; LLM draft is optional |
| R8 | Scope creep into AVM | Operational | 2 | 5 | Explicit out of scope; Chleo sign-off |

Likelihood × impact is qualitative. Residual risk after mitigations is **acceptable for a pilot, not for unsupervised send**.
