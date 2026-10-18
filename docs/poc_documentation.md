# POC documentation (Round 2)

## What to demo

1. **Python POC (always on):** `python src/run_poc.py`
2. **n8n:** import `n8n/workflow.json` (webhook → OpenAI → fail-closed parse)
3. **Recording:** 2–5 min screen capture of either path scoring eval_01 and eval_06. Store as `presentation/poc_demo.mp4` locally (not required in git if large).

## Evidence of a working demo

`evaluation/poc_actuals.jsonl` is the committed actual output of the rules engine on the golden set.

## What got stronger vs Round 1

- Same schema now feeds the Streamlit MVP
- Fail-closed parse documented
- Prompt file shared between n8n and `--llm`

## Honest limits

This is not connected to a production CRM. Token cost is negligible; **change-management** is the real cost. The POC does not prove conversion lift.
