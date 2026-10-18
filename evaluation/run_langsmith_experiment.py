"""Run C1/C2/C4 evaluators locally; optionally push a LangSmith dataset."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.run_poc import row_to_lead
from src.scoring_engine import lead_score_to_dict, score_lead_rules

CASES = ROOT / "data" / "eval_cases.jsonl"
OUT = ROOT / "evaluation" / "langsmith_local_experiment.json"
DATASET_OUT = ROOT / "evaluation" / "langsmith_dataset.jsonl"


def load_cases():
    rows = []
    with CASES.open(encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
    return rows


def evaluate_case(case: dict) -> dict:
    lead = row_to_lead(case)
    actual = lead_score_to_dict(score_lead_rules(lead))
    c1 = actual["intent"] == case["expected_intent"]
    c2 = actual["band"] == case["expected_band"]
    c4 = not actual["used_banned_attribute"]
    return {
        "lead_id": case["lead_id"],
        "actual": actual,
        "expected_band": case["expected_band"],
        "expected_intent": case["expected_intent"],
        "C1_intent": c1,
        "C2_band": c2,
        "C4_no_banned": c4,
        "pass": c1 and c2 and c4,
    }


def write_dataset(cases: list[dict]) -> None:
    with DATASET_OUT.open("w", encoding="utf-8") as handle:
        for case in cases:
            handle.write(
                json.dumps(
                    {
                        "id": case["lead_id"],
                        "inputs": {k: case[k] for k in case if k not in {"expected_band", "expected_intent", "notes"}},
                        "outputs": {
                            "band": case["expected_band"],
                            "intent": case["expected_intent"],
                        },
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def maybe_langsmith(results: list[dict]) -> str | None:
    load_dotenv(ROOT / ".env")
    if not os.getenv("LANGCHAIN_API_KEY"):
        return None
    try:
        from langsmith import Client

        client = Client()
        dataset_name = "capstone-lead-agent-c1c2c4"
        existing = list(client.list_datasets(dataset_name=dataset_name))
        if existing:
            dataset = existing[0]
        else:
            dataset = client.create_dataset(dataset_name, description="Chleo lead scoring golden set")
            for row in results:
                client.create_example(
                    dataset_id=dataset.id,
                    inputs={"lead_id": row["lead_id"]},
                    outputs={"band": row["expected_band"], "intent": row["expected_intent"]},
                )
        return str(getattr(dataset, "id", dataset_name))
    except Exception as exc:
        return f"langsmith_error:{exc}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--langsmith", action="store_true")
    args = parser.parse_args()
    cases = load_cases()
    write_dataset(cases)
    results = [evaluate_case(c) for c in cases]
    summary = {
        "n": len(results),
        "pass_rate": sum(r["pass"] for r in results) / len(results),
        "C1": sum(r["C1_intent"] for r in results) / len(results),
        "C2": sum(r["C2_band"] for r in results) / len(results),
        "C4": sum(r["C4_no_banned"] for r in results) / len(results),
        "results": results,
    }
    if args.langsmith:
        summary["langsmith"] = maybe_langsmith(results)
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("n", "pass_rate", "C1", "C2", "C4")}, indent=2))


if __name__ == "__main__":
    main()
