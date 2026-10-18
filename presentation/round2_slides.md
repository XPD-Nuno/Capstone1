# Round 2 final pitch (10–12 slides, ~10 min + Q&A)

Panel: CEO (ROI), Legal (liability), CTO (viability), Ops (disruption). Body text ≥24pt when in PowerPoint. One idea per slide.

| # | Slide | Point |
| --- | --- | --- |
| 1 | Title | Lead desk for an SME Portuguese agency — inspectable triage, human send |
| 2 | KEEP/CHANGE (30s) | Working assumption KEEP; update from `round1_decision.md` |
| 3 | Problem | Q1 2026: prices up, transactions down; too many portal leads for 8 agents |
| 4 | Solution | HOT/WARM/COLD + rationale + HITL draft. Not a robot agent. |
| 5 | POC demo | Webhook / `run_poc.py` — eval_01 vs spam |
| 6 | Business case | Break-even ≈ one extra instruction / year plus time, or one per quarter on the base story. Assumptions visible. |
| 7 | Top risks | Profiling, discrimination, shelfware, hallucination. Mitigations exist. |
| 8 | Compliance | AI Act: provisional not high-risk **if** no auto-deny. GDPR: LI + HITL + SCCs. We do not certify. |
| 9 | Deployment | 60-day one-office pilot with kill criteria, then offices 2–5 |
| 10 | **MVP demo** | Streamlit approve/reject. Required. Backup recording. |
| 11 | Ask | “Approve a 60-day shadow-mode pilot on Office 1, budget ~€10k.” |

## Likely Q&A

- Walk the AI Act reasoning without saying “limited risk” as a sticker  
- What if the model is wrong? Agent calls anyway; logs the override  
- Deletion: lead id + traces; subprocessors  
- Why not just ChatGPT? Uncontrolled paste is the current risk  
- Weakness if more time: live CRM calibration, EU-hosted model, red-team set
