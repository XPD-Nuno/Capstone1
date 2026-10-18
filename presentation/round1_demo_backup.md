# Round 1 demo backup

If the live n8n webhook fails:

```powershell
python data\generate_leads.py
python src\run_poc.py --input data\eval_cases.jsonl --output evaluation\poc_actuals.jsonl
python evaluation\build_eval_table.py
```

Show:

- `n8n/workflow.json` nodes (webhook → OpenAI → fail-closed parse → respond)
- `evaluation/scored_cases.csv` for pass/fail
- `charts/01_capacity_gap.png` and `charts/02_band_mix.png`

Record a 2-minute screen capture before the slot. The rubric rewards a working POC, not a heroic debug in front of Chleo.
