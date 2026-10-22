# Capstone — AI Lead Qualification for a Portuguese SME Estate Agency

Consulting pitch (Round 1) and working MVP (Round 2) for **Chleo**, CEO of a fictional SME residential estate agency in **Portugal** (~10–50 people, 2–5 offices).

**Primary use case:** score and prioritise buyer/seller enquiries so agents spend time on high-conversion leads. The AI never sends messages or rejects people on its own — an agent always decides.

Round 1 answers Chleo’s transparency concern **on paper** (criteria + scored cases). Round 2 answers it in **LangSmith**. Do **not** submit a LangSmith project in Round 1.

## Client snapshot

| Item | Starting choice (changeable after Round 1) |
| --- | --- |
| Sector | Residential real estate |
| Company size | SME agency, 10–50 people, 2–5 offices |
| Market | Portugal / EU |
| CEO | Chleo — “AI does not seem transparent” |

## Repository map

| Path | What it is |
| --- | --- |
| [research/](research/) | Sector notes, opportunities/risks, three use cases |
| [data/](data/) | Synthetic leads + generation script (no live client PII) |
| [charts/](charts/) | 6 stakeholder charts + documentation |
| [n8n/](n8n/) | Importable POC workflow, prompt, docs |
| [evaluation/eval_plan.md](evaluation/eval_plan.md) | Round 1 paper eval (no LangSmith) |
| [cost_estimation/](cost_estimation/) | Cost, timeline, assumptions |
| [feedback/round1_decision.md](feedback/round1_decision.md) | Fill **after** the staff pitch (KEEP/CHANGE) |
| [presentation/](presentation/) | Round 1 and Round 2 slide outlines |
| [src/](src/) | Shared scoring engine used by charts, eval, Python POC, and MVP |
| [mvp/](mvp/) | Round 2 Streamlit + LangGraph app (HITL) |
| [docs/](docs/) | Round 2 consulting package (ROI, GDPR, EU AI Act, strategy, MVP/POC docs) |

## Round 1 — how to run

```powershell
cd "C:\Users\NunoAlmeida\OneDrive - Transparity\Documents\Pessoal\IronHack\CapStone"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python data\generate_leads.py
python charts\generate_charts.py
python src\run_poc.py --input data\eval_cases.jsonl --output evaluation\poc_actuals.jsonl
```

Charts land in `charts/*.png`. The Python POC uses the **same rules** as the n8n prompt so the scored mini-set is reproducible without a live n8n host.

To run the optional LLM path (same JSON schema as n8n):

```powershell
copy .env.example .env
# edit .env and set OPENAI_API_KEY
python src\run_poc.py --llm --input data\eval_cases.jsonl --output evaluation\poc_actuals_llm.jsonl
```

Import `n8n/workflow.json` into n8n Cloud or self-hosted n8n and follow [n8n/workflow_documentation.md](n8n/workflow_documentation.md).

## Round 2 — MVP

```powershell
copy .env.example .env
# set OPENAI_API_KEY; optionally LANGCHAIN_API_KEY for traces
streamlit run mvp\app.py
```

Tests: `pip install -r requirements-dev.txt` then `python -m pytest`. Bash and PowerShell commands are in [docs/mvp_documentation.md](docs/mvp_documentation.md).

LangSmith experiment notes: [evaluation/langsmith.md](evaluation/langsmith.md).

## Constraints

- Public or **synthetic** data only. No real CRM contacts.
- One working capability beats four incomplete screens.
- Compliance documents are a **consultant first-pass**, not a legal certification.

## Author

Ironhack AI Consulting capstone — individual project, Weeks 20–24.
