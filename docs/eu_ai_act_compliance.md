# EU AI Act — first-pass (consultant, not a lawyer)

This is a **navigator** memo for Chleo. It is not a conformity assessment, not CE marking advice, and not a guarantee. High-risk design choices (thresholds, oversight, model) should be **approved in writing by the client**.

## System in one paragraph

A lead-triage assistant for estate agents: it classifies enquiries and suggests a next action and an optional draft. A human must approve drafts. It does not allocate housing, set prices, score credit, or interact autonomously with the public as a bot in this MVP.

## Role map

| Actor | Role in this engagement | Comment |
| --- | --- | --- |
| OpenAI (or other GPAI host) | GPAI **provider** of the underlying model | Their GPAI obligations ≠ Chleo’s product obligations |
| Student consultant / implementer | Puts a system in Chleo’s hands | If we **put our own brand** on a product we sell, we may become a **provider**. If we only advise and Chleo deploys our scripts internally, Chleo is closer to **deployer** of a custom system. **Write this down in the SOW.** |
| Chleo’s agency | **Deployer** (and possibly provider if they commercialise it to franchisees) | Decides thresholds, HITL, notices |
| n8n / LangSmith / cloud host | Processors / supporting tools | In the GDPR pack, not AI Act providers of the lead-scoring system |

Recommended SOW line: *“We deliver a custom internal tool. Chleo is deployer. We do not place a CE-marked product on the EU market under our brand.”* If that changes, stop and re-map.

## Risk classification (provisional)

**Working classification: not high-risk under Annex III**, provided that:

- the system does **not** decide access to essential private services in the sense of credit/insurance-style scoring
- it does **not** replace the agent on housing allocation
- it is **not** a prohibited social-scoring or untargeted scrape of faces
- it is **not** a biometric categorisation tool

Lead **prioritisation for a commercial sales team** is closer to **minimal / no specific AI Act use-case** plus, if a consumer-facing chatbot were added later, **Art. 50 transparency** (disclose that it is AI).

**Weaker argument we considered and reject for now:** “housing is essential, therefore high-risk.” The MVP does not grant or deny a home; it ranks a salesperson’s call list. If Chleo later auto-blocks viewings for ‘COLD’ people, **reclassify immediately** — that design would need a new memo and likely legal counsel.

GPAI transparency obligations sit on the model provider. Chleo still needs logs and instructions because **deployers** of GPAI systems have practical duties (instructions, monitoring).

## Obligations we still treat as good practice (even if not high-risk)

| Practice | Why |
| --- | --- |
| Logging of score, version, override | Debuggability + future high-risk jump |
| Human oversight that is not a rubber stamp | GDPR Art. 22 posture |
| Accuracy/robustness eval (LangSmith) | Chleo’s transparency complaint |
| Technical documentation outline (below) | So we are not empty-handed if the use case hardens |
| Incident process | Even a “wrong HOT” that causes a harassing call is an ops incident |

We **do not** claim CE, EU database registration, or 15-day serious-incident reporting as currently applicable. If counsel later says Annex III applies, those clocks matter (including faster reporting for certain harms).

## Conformity summary (honest)

| Question | Answer |
| --- | --- |
| Is this certified? | No |
| Prohibited? | No, on the current design |
| High-risk? | Provisional **no**, design-dependent |
| Transparency (Art. 50) for this MVP? | Agents know it is AI; consumers are not chatting with it |
| Residual? | Revisit if auto-deny, public bot, or franchise productisation |

## Technical documentation outline (if we ever need a full file)

1. System description and intended purpose  
2. Role map and versions of prompts/models  
3. Data: training (none of ours) vs operational inputs  
4. Human oversight protocol  
5. Metrics: C1–C5, agreement rate, incident log  
6. Risk management notes (bias, injection)  
7. Post-market monitoring: weekly sample in pilot  

## Gaps / remediation

- No formal legal opinion  
- No notified body  
- Student project uses synthetic data only  
- Need Chleo written acceptance of “COLD ≠ housing denial”
