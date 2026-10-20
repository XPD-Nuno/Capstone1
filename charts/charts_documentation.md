# Charts documentation

**Tool:** Python 3, Matplotlib (`charts/generate_charts.py`). Static PNGs on purpose — the Round 1 rubric does not reward a dashboard.

**CRM figures** come from `data/synthetic_leads.csv` scored by `src/scoring_engine.py` (rules-v1). Treat them as a **scenario**, not Chleo’s audited books.

**Market figures** come from INE (see `research/sector_research.md`).

Regenerate:

```powershell
python data\generate_leads.py
python charts\generate_charts.py
```

| File | Stakeholder point | Metric | Why Chleo should care | Source |
| --- | --- | --- | --- | --- |
| `00_ine_market.png` | The national tape changed in 2026 | HPI vs transaction YoY | Calling every lead made more sense in a rising *volume* market. Q1 2026 volume fell while prices rose. | INE HPI 2025 and Q1 2026 |
| `01_capacity_gap.png` | Capacity, not marketing, is the constraint | 180 weekly enquiries vs 8 agents × 6 quality conversations × 5 days | Buying more portal credits without triage burns seniors | Synthetic weekly book of 180 leads; capacity assumption documented below |
| `02_band_mix.png` | Most leads are not “call now” | Count of HOT / WARM / COLD after rules-v1 | Shows what the AI actually does: a distribution, not magic | Synthetic + scorer |
| `03_intent_mix.png` | Rent and unclear intent clog a sales-led SME | Intent mix | Lets Chleo decide whether lettings get a different queue | Synthetic + scorer |
| `04_geography.png` | Demand is lumpy | Leads by city | One national playbook is wrong; Lisboa/Porto dominate | Synthetic, weighted toward INE-hot geographies |
| `05_delay_cost.png` | Slow follow-up is a revenue leak | Illustrative expected commission, fast vs slow touch | CEO language for the 60-day pilot ask | Assumptions below — **not** measured on live deals |
| `06_opportunity_risk.png` | Where to start | Opportunity vs governance risk | Why we POC scoring, not an AVM | Consultant scores in `research/opportunities_risks.md` |
| `capstone1_product_workflow.html` | Full product day-flow beyond Round 1 MVP | Interactive viz: Capture → Store → Score → Match → Draft → HITL → Audit/Quota + 7 topic tabs (intake, repo, bands, filters, tool ladder, HITL, cost/admin) | Pitch-ready story for channel priority, lasting lead memory, complete HOT/WARM/COLD + gaps, property match, scrape/API ladder, prepaid quotas — still draft+HITL only | Product blueprint (`docs/product_architecture_v2.md`); complements overview + user-journey HTML |

## Assumptions (must stay visible)

- **8 agents** on the floor, **6** high-quality live conversations per agent per day before quality drops. That is a planning number, not a time-and-motion study.
- **Delay chart:** completed-deal commission **€12,000**; conversion if contacted <1h vs >8h: HOT 18%→8%, WARM 6%→4%, COLD 1%→1%. Replace with Chleo’s CRM in a real discovery.
- Scorer **does not** use nationality, gender, or “good neighbourhood”. City is used only as a display dimension, not a penalty.

## What these charts do **not** prove

They do not prove that deploying the POC will lift conversion by X%. They prove we can *talk* about capacity, mix, and delay in Chleo’s language, and that the POC’s output distribution is inspectable.
