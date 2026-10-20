from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lead_desk.config import Settings  # noqa: E402
from lead_desk.schema import Channel, Lead  # noqa: E402

EVAL_CASES = ROOT / "data" / "eval_cases.jsonl"


def eval_case_to_lead(case: dict) -> Lead:
    return Lead(
        lead_id=case["lead_id"] if case["lead_id"].startswith("lead_") else "lead_" + case["lead_id"],
        channel=Channel.EMAIL,
        source=case.get("channel", "website"),
        city=case.get("city"),
        message=case["message"],
        budget_eur=case.get("budget_eur"),
        timeline_days=case.get("timeline_days"),
        property_views_7d=case.get("property_views_7d", 0),
        saved_listings=case.get("saved_listings", 0),
        replied_to_agent=case.get("replied_to_agent", False),
        phone_provided=case.get("phone_provided", False),
        email_provided=case.get("email_provided", True),
    )


@pytest.fixture
def eval_cases() -> list[dict]:
    with EVAL_CASES.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


@pytest.fixture
def settings() -> Settings:
    return Settings(db_path=":memory:")
