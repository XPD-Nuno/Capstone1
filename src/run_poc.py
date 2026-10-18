"""Run the Round 1 POC scorer over eval cases or a CSV of leads."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.scoring_engine import LeadInput, lead_score_to_dict, parse_llm_json, score_lead_rules

PROMPT_PATH = ROOT / "n8n" / "prompts" / "lead_scoring_v1.md"


def _empty_to_none(value):
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def row_to_lead(row: dict) -> LeadInput:
    budget = _empty_to_none(row.get("budget_eur"))
    timeline = _empty_to_none(row.get("timeline_days"))
    return LeadInput(
        lead_id=str(row["lead_id"]),
        channel=str(row.get("channel") or "website"),
        city=str(row.get("city") or "Lisboa"),
        message=str(row["message"]),
        budget_eur=int(budget) if budget is not None else None,
        timeline_days=int(timeline) if timeline is not None else None,
        property_views_7d=int(row.get("property_views_7d") or 0),
        saved_listings=int(row.get("saved_listings") or 0),
        replied_to_agent=str(row.get("replied_to_agent")).lower() in {"true", "1", "yes"},
        phone_provided=str(row.get("phone_provided")).lower() in {"true", "1", "yes"},
        email_provided=str(row.get("email_provided", True)).lower() not in {"false", "0", "no"},
    )


def score_with_llm(lead: LeadInput) -> dict:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-your"):
        raise SystemExit("OPENAI_API_KEY missing. Copy .env.example to .env")
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    payload = lead.model_dump()
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    )
    parsed = parse_llm_json(response.choices[0].message.content or "{}")
    parsed["lead_id"] = lead.lead_id
    parsed["model_version"] = model
    return parsed


def iter_inputs(path: Path):
    if path.suffix == ".jsonl":
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield json.loads(line)
        return
    with path.open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "eval_cases.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation" / "poc_actuals.jsonl")
    parser.add_argument("--llm", action="store_true")
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for raw in iter_inputs(args.input):
        lead = row_to_lead(raw)
        result = score_with_llm(lead) if args.llm else lead_score_to_dict(score_lead_rules(lead))
        rows.append(result)

    with args.output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} scores to {args.output}")


if __name__ == "__main__":
    main()
