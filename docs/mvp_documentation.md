# MVP documentation

## What it is

A Streamlit “lead desk” with a LangGraph of two nodes (`score` → `draft`). The third step is **human**: Approve or Reject. There is no send API.

```powershell
streamlit run mvp\app.py
```

## How someone else starts it

1. Python 3.11+ recommended  
2. `python -m venv .venv` and `pip install -r requirements.txt`  
3. Copy `.env.example` → `.env` (OpenAI optional; rules engine always works)  
4. `streamlit run mvp/app.py`

## Error handling

- Invalid lead payloads fail Pydantic validation before the graph runs.
- LLM draft errors fall back to a template in Portuguese.
- Banned-attribute flag surfaces as a blocking warning in the UI.
- Status cannot skip to `ready` without the Approve click.

## What “core AI capability” means here

The running capability is **qualification**: a structured band + rationale. Drafting is assistive and gated.

## What we refused to build

Four extra screens (analytics, campaign builder, valuation, public chatbot). Rubric: one path that works.
