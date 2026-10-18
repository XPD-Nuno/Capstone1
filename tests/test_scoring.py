from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.run_poc import row_to_lead
from src.scoring_engine import score_lead_rules


def test_eval_cases_match_expected_bands():
    path = ROOT / "data" / "eval_cases.jsonl"
    with path.open(encoding="utf-8") as handle:
        cases = [json.loads(line) for line in handle]
    for case in cases:
        score = score_lead_rules(row_to_lead(case))
        assert score.band.value == case["expected_band"], (case["lead_id"], score.band, score.score_0_100, score.rationale)
        assert score.intent.value == case["expected_intent"], (case["lead_id"], score.intent)
        assert score.used_banned_attribute is False
