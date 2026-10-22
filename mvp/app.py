"""HITL lead desk — one capability: score, draft, approve. Nothing is sent."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mvp.graph import LEAD_GRAPH, apply_decision

st.set_page_config(page_title="Chleo Lead Desk", layout="wide")
st.title("Lead desk — score, then a human decides")
st.caption("Synthetic / training use only. This app never sends email, SMS, or WhatsApp.")

with st.sidebar:
    st.markdown("**Allowed signals:** intent, budget, timing, views, contactability.")
    st.markdown("**Banned:** nationality, race, gender, religion, ‘bad neighbourhood’ as quality.")
    st.markdown("**Status:** `pending_approval` until you click Approve.")

col_in, col_out = st.columns(2)

with col_in:
    st.subheader("Incoming enquiry")
    lead_id = st.text_input("Lead ID", "lead_demo_01")
    city = st.selectbox(
        "City",
        ["Lisboa", "Porto", "Cascais", "Braga", "Coimbra", "Faro", "Sintra", "Oeiras"],
    )
    channel = st.selectbox("Channel", ["website", "idealista", "imovirtual", "referral", "walk-in"])
    message = st.text_area(
        "Message",
        "Quero comprar T2 em Lisboa. Orçamento 380 mil. Posso visitar amanhã à tarde.",
        height=140,
    )
    budget = st.number_input("Budget EUR (0 = unknown)", min_value=0, value=380000, step=1000)
    timeline = st.number_input("Timeline days (0 = unknown)", min_value=0, value=21, step=1)
    views = st.slider("Listing views (7d)", 0, 30, 12)
    saved = st.slider("Saved listings", 0, 15, 4)
    phone = st.checkbox("Phone provided", True)
    replied = st.checkbox("Already replied to an agent", True)
    run = st.button("Score this lead", type="primary")

if run:
    lead = {
        "lead_id": lead_id,
        "channel": channel,
        "city": city,
        "message": message,
        "budget_eur": int(budget) or None,
        "timeline_days": int(timeline) or None,
        "property_views_7d": int(views),
        "saved_listings": int(saved),
        "replied_to_agent": replied,
        "phone_provided": phone,
        "email_provided": True,
    }
    result = LEAD_GRAPH.invoke({"lead": lead})
    st.session_state["result"] = result
    st.session_state["draft_box"] = result.get("draft", "")


def _decide(status: str) -> None:
    # Runs before the rerun renders, so the status line below is never stale.
    st.session_state["result"] = apply_decision(
        st.session_state["result"], status, st.session_state.get("draft_box", "")
    )


result = st.session_state.get("result")

with col_out:
    st.subheader("Model output (not a decision)")
    if not result:
        st.info("Submit a lead to see band, rationale, and a draft.")
    else:
        score = result["score"]
        st.metric("Band", score["band"])
        st.write(f"Intent **{score['intent']}** · score **{score['score_0_100']}** · engine `{score['model_version']}`")
        st.write(score["rationale"])
        st.write("**Suggested next action:**", score["next_action"])
        if score.get("used_banned_attribute"):
            st.error("Guardrail: banned attribute detected in rationale. Do not use this output.")
        st.text_area("Draft for the agent to edit", height=180, key="draft_box")
        c1, c2 = st.columns(2)
        c1.button("Approve — ready for the agent to send", on_click=_decide, args=("approved",))
        c2.button("Reject — do not use this draft", on_click=_decide, args=("rejected",))
        status = result.get("status", "pending_approval")
        st.write("Workflow status:", status)
        if status == "approved":
            st.success("Marked approved with the draft as edited above. Still not sent. Copy out of this screen if needed.")
        elif status == "rejected":
            st.warning("Rejected. Lead stays in the human queue without this draft.")

st.divider()
st.markdown(
    "Logs for a real deployment would store lead id, score version, override, and actor — not full message text if it is not needed (minimisation)."
)
