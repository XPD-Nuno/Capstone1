# Round 1 presentation (~5–7 min) — speaker notes

Audience: teaching staff as Chleo. Class may play ops / legal-curious / tech-curious.

**Backup if n8n is down:** `python src/run_poc.py` and `evaluation/poc_actuals.jsonl`.

| Time | Slide | Say this, not that |
| --- | --- | --- |
| 0:00 | Title | “Independent Portuguese agency, 10–50 people. Chleo does not trust ‘the AI’. This meeting is about **triage you can inspect**, not a robot estate agent.” |
| 1:00 | Market | INE: prices still up in 2025/Q1 2026, **transactions down** in Q1 2026. Calling everyone is the wrong response. |
| 1:30 | Use cases | Three ideas. We only POC **UC-1 scoring**. Drafts and INE briefings wait. AVM is out — too much liability. |
| 2:00–4:00 | Charts | Show 4: capacity gap, band mix, INE volume vs price, delay cost. One sentence each. “Assumptions are written down.” |
| 4:00–6:00 | POC + eval | Walk eval_01 (HOT) and eval_06 (spam COLD). Criteria C1–C5. “LangSmith is Round 2. Today is a scored paper set.” |
| 6:00–7:00 | Cost / ask | Base pilot ~€10k one-off, ~€500/month, 60 days, **one office**, no auto-send. Ask: “May we run a shadow-mode pilot?” |
| Close | Feedback wanted | “Where is this too generic? Which chart is CEO-ready? What would legal block?” |

## Slide list (max ~8)

1. Title — Lead triage for Chleo, SME Portugal
2. The job — too many portal leads, not enough senior hours
3. INE snapshot — price up, Q1 2026 volume down
4. Three use cases — only UC-1 in the POC
5. Charts collage (capacity + bands)
6. Live / backup POC
7. How we know it works — 7 cases, 5 criteria
8. 60-day ask + cost assumptions

Export to PDF as `presentation/round1_slides.pdf` before the slot if the instructor wants a file. This markdown is the content source.

## Demo script (90 seconds)

1. Open `data/eval_cases.jsonl` eval_01.
2. Run or show precomputed `evaluation/poc_actuals.jsonl`.
3. Point at `band`, `rationale`, `next_action`.
4. Repeat eval_07: “from abroad” must not appear as a quality judgement.
