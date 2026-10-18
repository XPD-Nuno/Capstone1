"""Refresh evaluation/scored_cases.csv from eval cases + poc actuals."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "data" / "eval_cases.jsonl"
ACTUALS = ROOT / "evaluation" / "poc_actuals.jsonl"
OUT = ROOT / "evaluation" / "scored_cases.csv"


def load_jsonl(path: Path) -> dict:
    rows = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rows[row["lead_id"]] = row
    return rows


def main() -> None:
    cases = load_jsonl(CASES)
    actuals = load_jsonl(ACTUALS)
    fieldnames = [
        "lead_id",
        "input_short",
        "expected_band",
        "expected_intent",
        "actual_band",
        "actual_intent",
        "actual_score",
        "rationale",
        "next_action",
        "c1_intent",
        "c2_band",
        "c4_banned",
        "case_pass",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for lead_id, case in cases.items():
            actual = actuals[lead_id]
            c1 = actual["intent"] == case["expected_intent"]
            c2 = actual["band"] == case["expected_band"]
            c4 = not actual.get("used_banned_attribute", False)
            writer.writerow(
                {
                    "lead_id": lead_id,
                    "input_short": case["message"][:80],
                    "expected_band": case["expected_band"],
                    "expected_intent": case["expected_intent"],
                    "actual_band": actual["band"],
                    "actual_intent": actual["intent"],
                    "actual_score": actual["score_0_100"],
                    "rationale": actual["rationale"],
                    "next_action": actual["next_action"],
                    "c1_intent": "pass" if c1 else "fail",
                    "c2_band": "pass" if c2 else "fail",
                    "c4_banned": "pass" if c4 else "fail",
                    "case_pass": "pass" if c1 and c2 and c4 else "fail",
                }
            )
    print("wrote", OUT)


if __name__ == "__main__":
    main()
