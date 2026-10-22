# Scoring rules: `rules-v1` vs `rules-v1.2`

The repo has two deterministic scorers.

| Version | Code | Used by |
| --- | --- | --- |
| `rules-v1` | `src/scoring_engine.py::score_lead_rules` | Round 1 POC (`src/run_poc.py`), the n8n workflow and its prompt (`n8n/prompts/lead_scoring_v1.md`), the Streamlit/LangGraph MVP (`mvp/`), charts, `tests/test_scoring.py`, and the Round 1 slides and docs |
| `rules-v1.2` | `lead_desk/scoring.py::score_lead` (default `strict_policy=True`) | Lead Desk: CLI, API and web dashboard |

`score_lead(lead, strict_policy=False)` reproduces `rules-v1` exactly (parity is tested in `lead_desk/tests/test_classifier.py`). `rules-v1.2` applies the client decisions of 20 Oct 2026. The Round 1 material is left as it was presented, so anything quoting bands from the slides or `docs/` refers to `rules-v1`.

## What is the same

- Inputs: intent, budget, timeline, listing views and saves in the last 7 days, phone provided, previous reply, email provided. Nationality, neighbourhood and language ability are never inputs.
- The points table: base 10, buy/sell +25, rent +8, seller +12 / budget +15, timeline +20 / +10 / +2, activity +12 / +6, contactable +10, browsing −20, spam −40, clamped to 0–100. The numeric score of a lead is identical under both versions.
- The rationale format: `Score uses only operational signals (...). reason; reason; .... Numeric score=N.`

## Differences

| # | Topic | `rules-v1` | `rules-v1.2` |
| --- | --- | --- | --- |
| 1 | HOT gate | buy/sell and score ≥ 70 | buy/sell, score ≥ 70, **and** (timeline ≤ 90 days or views ≥ 8 or saved ≥ 3), **and** a phone number or a previous reply |
| 2 | HOT without phone or reply | HOT, next action "email/WhatsApp in 2 hours asking for a phone number" | WARM ("held at WARM: no phone number or reply yet"), or COLD if email-only (row 3) |
| 3 | Email-only leads (email, no phone, no previous reply) | No special rule | COLD with the next action "reply by email with one qualifying question, ask for a phone number, do not phone" |
| 4 | Rental intent | Always COLD ("route to lettings") | WARM ("lettings lead … after HOT sales leads"), never HOT. Still COLD when spam, browsing with score < 35, or email-only |
| 5 | Browsing | COLD only if the score drops below 35 | Same threshold, checked before the rent and email-only rules |
| 6 | Intent keywords | Seed lists | Seed lists plus `selling`, `listar o/a`, `pôr/por/colocar à venda`, `buying`, `purchase` (phrasings in `data/synthetic_leads.csv` the seed missed) |
| 7 | Guardrail | Substring match on the rationale against 18 terms (so `terrace` would trip `race`) | Whole-word match on the rationale and the next action against the seed list plus ethnicity, disability, sexual orientation, family/marital status, pregnancy, neighbourhood-as-quality and language-ability terms (`lead_desk/guardrail.py`) |
| 8 | Logistics notes | None | Separate hints such as "offer a video viewing" when a lead writes from abroad, or the portal listing reference. They are shown to the agent and never feed the score |

`rules-v1.1` was the intermediate step that only added the keywords in row 6. It was never released under its own label.

## Effect on the eval mini-set (`data/eval_cases.jsonl`)

| Case | Expected (Round 1) | `rules-v1` | `rules-v1.2` | Why |
| --- | --- | --- | --- | --- |
| eval_01 | HOT | HOT | HOT | |
| eval_02 | HOT | HOT | HOT | |
| **eval_03** | WARM | WARM | **COLD** | Row 3: buy intent, budget 250 000 €, timeline 300 days, score 66, but only an email address (no phone, no reply) |
| eval_04 | COLD | COLD | COLD | |
| eval_05 | COLD | COLD | COLD | Same band, different reason: under v1.2 the rental would be WARM (row 4), but it is email-only (row 3) |
| eval_06 | COLD | COLD | COLD | |
| eval_07 | HOT | HOT | HOT | |

The expected labels in `data/eval_cases.jsonl` are the Round 1 (`rules-v1`) labels. Lead Desk tests apply a documented override for eval_03 (`V12_OVERRIDES` in `lead_desk/tests/test_classifier.py`). The numeric score of eval_03 is 66 under both versions; only the band changes.

## Open points

- The HOT/WARM/COLD criteria are to be revisited once Lead Desk runs on real situations (client decision, 20 Oct 2026).
- Before Round 2 the team should decide whether the n8n POC, the MVP and the slides move to `rules-v1.2` or keep `rules-v1` as the "Round 1 baseline". Until then, quote the version next to any band.
