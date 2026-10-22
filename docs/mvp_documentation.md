# MVP documentation

## What it is

A Streamlit “lead desk” with a LangGraph of two nodes (`score_lead` → `write_draft`). The third step is **human**: Approve or Reject. There is no send API.

## How someone else starts it

Python 3.11+ recommended. OpenAI is optional; the rules engine always works. `requirements.txt` is enough to run the app; `requirements-dev.txt` adds pytest for the test suite.

Bash (macOS / Linux):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
streamlit run mvp/app.py
python -m pytest
```

PowerShell (Windows):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
streamlit run mvp\app.py
python -m pytest
```

## Human decision

Approve and Reject set status to `approved` / `rejected` and save the draft text **as edited in the box**, so the approved record is what the human signed off, not the raw model draft. Scoring a new lead resets the box to the new model draft.

## Error handling

- Invalid lead payloads fail Pydantic validation before the graph runs.
- LLM draft errors fall back to a template in Portuguese.
- Banned-attribute flag surfaces as a blocking warning in the UI.
- Status starts at `pending_approval` and only becomes `approved` (or `rejected`) by a human click.

## What “core AI capability” means here

The running capability is **qualification**: a structured band + rationale. Drafting is assistive and gated.

## What we refused to build

Four extra screens (analytics, campaign builder, valuation, public chatbot). Rubric: one path that works.
