from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.run_poc import row_to_lead


def _load_eval_cases():
    path = ROOT / "data" / "eval_cases.jsonl"
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def test_graph_runs_eval_cases_with_expected_bands(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from mvp.graph import build_graph

    graph = build_graph()
    cases = _load_eval_cases()
    assert cases
    for case in cases:
        lead = row_to_lead(case).model_dump()
        result = graph.invoke({"lead": lead})
        score = result["score"]
        assert score["band"] == case["expected_band"], (case["lead_id"], score)
        assert score["intent"] == case["expected_intent"], (case["lead_id"], score)
        assert score["used_banned_attribute"] is False
        assert result["draft"].strip()
        assert result["status"] == "pending_approval"
