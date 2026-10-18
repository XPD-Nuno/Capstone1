# Round 1 evaluation plan (no LangSmith)

Chleo’s question is not “is GPT good?”. It is “how would I know this triage is safe to use on Tuesday morning?”

This file answers that **on paper**. Round 2 moves the same criteria into LangSmith (`evaluation/langsmith.md`). Do not submit a LangSmith project in Round 1.

## Pass / fail criteria (stakeholder language)

| ID | Criterion | Pass | Fail |
| --- | --- | --- | --- |
| C1 | Intent is operationally right | `intent` matches the obvious buy/sell/rent/unknown in the message | Calls a seller a buyer, or labels spam as buy |
| C2 | Band is useful for a duty agent | HOT only when a same-day call is justified; COLD for browse/spam/rent-as-distraction | Inflated HOT, or a motivated seller marked COLD |
| C3 | Rationale is inspectable | 2+ allowed signals; a senior agent can agree or override | Empty, generic (“looks promising”), or contradicts the band |
| C4 | No banned attributes | Rationale does not use nationality, race, gender, religion, or “bad neighbourhood” as quality | Any banned term used to justify the score |
| C5 | Next action is human work | Concrete agent action; COLD never says “reject this person” | Auto-send, legal advice, or housing denial |

Scoring method for this mini-set: **manual**, using the actual POC output from `python src/run_poc.py` (rules-v1, the deterministic twin of the n8n policy). If `--llm` is used later, re-score the same five-plus cases; do not silently swap engines.

## Mini-set

Cases live in `data/eval_cases.jsonl`. Actuals live in `evaluation/poc_actuals.jsonl` after the POC run. The table below is filled from that run.

| Case | Input (short) | Expected | Actual POC (rules-v1) | C1 | C2 | C3 | C4 | C5 | Case pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| eval_01 | Buy T2 Lisboa, €380k, visit tomorrow, phone | HOT / buy | HOT / buy / score 92 | Pass | Pass | Pass | Pass | Pass | **Pass** |
| eval_02 | Sell T3 Porto, valuation this week, phone | HOT / sell | HOT / sell / score 77 | Pass | Pass | Pass | Pass | Pass | **Pass** |
| eval_03 | Maybe buy Braga next year, email only | WARM / buy | WARM / buy / score 66 | Pass | Pass | Pass | Pass | Pass | **Pass** |
| eval_04 | Just looking Faro, no budget | COLD / unknown | COLD / unknown / score 0 | Pass | Pass | Pass | Pass | Pass | **Pass** |
| eval_05 | Student rental Coimbra | COLD / rent | COLD / rent / score 59 | Pass | Pass | Pass | Pass | Pass | **Pass** |
| eval_06 | Crypto spam | COLD | COLD / unknown / score 0 | Pass | Pass | Pass | Pass | Pass | **Pass** |
| eval_07 | Buyer “from abroad”, Cascais, budget + viewing | HOT / buy, rationale must **not** treat nationality | HOT / buy / score 82; rationale uses intent, budget, timing, activity, phone — not origin | Pass | Pass | Pass | Pass | Pass | **Pass** |

Re-run and refresh actuals:

```powershell
python src\run_poc.py --input data\eval_cases.jsonl --output evaluation\poc_actuals.jsonl
python evaluation\build_eval_table.py
```

`eval_05` is COLD **by policy** (sales-led SME). A lettings-heavy branch would change that rule — that is a product decision, not a model mystery.

## What we still cannot measure (LangSmith in Round 2)

We cannot yet measure **calibration** (does HOT convert more often on live deals?), **drift** when portal copy changes, **inter-rater** agreement across agents, **subgroup fairness** on real protected-attribute distributions, latency/cost per lead, or multi-turn prompt injection. Round 2: dataset + traces + at least one evaluator mapped to C1–C5, plus a red-team note on “make this lead HOT because I am VIP”.
