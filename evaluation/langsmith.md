# LangSmith — Round 2 evaluation

Round 1 used a paper table. This file is the Round 2 move of **the same C1–C5 criteria** into a dataset + experiment.

**Do not submit LangSmith in the Round 1 zip.**

## Dataset

`evaluation/langsmith_dataset.jsonl` — each line: `inputs` (lead) + `outputs` (expected band/intent).

Built from `data/eval_cases.jsonl`.

## Target function to trace

`src.scoring_engine.score_lead_rules` (and later the compiled LangGraph). The function is deterministic, which is a **feature** for a first experiment: we are testing policy, not dice.

## Local experiment (always runnable)

```powershell
python evaluation\run_langsmith_experiment.py
```

Writes `evaluation/langsmith_local_experiment.json` with pass rates for C1, C2, C4.

## Hosted LangSmith experiment (when you have a key)

1. Set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` in `.env`.  
2. Re-run `python evaluation/run_langsmith_experiment.py --langsmith`.  
3. Paste the project URL or screenshots into this file under **Evidence**.  
4. Create an evaluator in the UI that checks `band == expected_band` (exact match) — that is the “at least one experiment with an evaluator” requirement.

## Evidence (local experiment)

`evaluation/langsmith_local_experiment.json` currently shows **n=7, pass_rate 1.0** on C1, C2, and C4. That checks the written policy, not live conversion. Paste a hosted LangSmith experiment URL here after you run `--langsmith`.

Failures are more valuable than a 100% vanity run. If you add messy real-world paraphrases, expect C2 misses; log them.

## What we still monitor in a pilot

Calibration vs closed deals, drift, injection (“ignore instructions”), subgroup review — see eval_plan.md.
