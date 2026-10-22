from pathlib import Path
import sys

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mvp.graph import apply_decision

APP = str(ROOT / "mvp" / "app.py")


def test_apply_decision_records_edited_draft():
    state = {"draft": "model draft", "status": "pending_approval"}
    out = apply_decision(state, "approved", "human edited draft")
    assert out["status"] == "approved"
    assert out["draft"] == "human edited draft"
    assert state["draft"] == "model draft"
    with pytest.raises(ValueError):
        apply_decision(state, "sent", "x")


def _button(at, prefix):
    return next(b for b in at.button if b.label.startswith(prefix))


def _status_line(at):
    return next(m.value for m in at.markdown if m.value.startswith("Workflow status:"))


def _scored_app(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    _button(at, "Score this lead").click().run()
    assert not at.exception
    return at


def test_approve_saves_edited_draft_and_status_is_fresh(monkeypatch):
    at = _scored_app(monkeypatch)
    assert "pending_approval" in _status_line(at)
    at.text_area(key="draft_box").input("Olá — texto revisto pelo consultor.").run()
    _button(at, "Approve").click().run()
    assert not at.exception
    result = at.session_state["result"]
    assert result["status"] == "approved"
    assert result["draft"] == "Olá — texto revisto pelo consultor."
    assert "approved" in _status_line(at)
    assert at.success


def test_reject_updates_status_on_same_run(monkeypatch):
    at = _scored_app(monkeypatch)
    _button(at, "Reject").click().run()
    assert not at.exception
    assert at.session_state["result"]["status"] == "rejected"
    assert "rejected" in _status_line(at)
    assert at.warning


def test_rescoring_replaces_draft_box(monkeypatch):
    at = _scored_app(monkeypatch)
    at.text_area(key="draft_box").input("stale edit").run()
    _button(at, "Score this lead").click().run()
    assert at.text_area(key="draft_box").value == at.session_state["result"]["draft"]
