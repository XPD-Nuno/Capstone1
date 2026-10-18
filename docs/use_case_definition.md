# Use case definition (Round 2)

## Evolution from Round 1

Round 1 pitched three use cases and proved UC-1 with a webhook-style scorer and a paper eval. Round 2 **keeps** the Portuguese SME residential framing unless `feedback/round1_decision.md` is updated to CHANGE after the staff pitch.

KEEP working assumption: same industry, same size, same primary use case. What changed technically: LangGraph + Streamlit HITL + LangSmith-ready dataset.

## Company profile

Independent residential agency, Portugal, 10–50 staff, 2–5 offices, sales-led with some lettings, portal-heavy intake, no ML team.

## Problem

Duty agents cannot give every Idealista/website enquiry the same speed. HOT buyers and motivated sellers wait behind browsers and spam. Consumer ChatGPT is already in the shadows.

## Solution

An inspectable **lead desk**: structured score (HOT/WARM/COLD) + rationale + next action + optional draft. A human must approve before a draft is “ready”. Nothing is auto-sent.

## Stakeholders

| Stakeholder | Care-about |
| --- | --- |
| Chleo (CEO) | Transparency, ROI, not a scandal |
| Duty agents | Speed, not more admin |
| Ops manager | Logs, overrides, simple runbook |
| DPO / lawyer (external, light) | Profiling, retention, processors |
| Enquirers | Fair treatment, a way to object |

## Success criteria (pilot)

- Senior-agent agreement on HOT ≥ 90% on a weekly 30-lead sample
- HOT first-touch median < 60 minutes in office hours
- 0 outbound messages without human approval
- 0 production use of banned attributes in rationales (audit sample)

## Out of scope

Auto-send, AVM, credit scoring, scraping portals, chatbots that negotiate, national rollout in month one.
