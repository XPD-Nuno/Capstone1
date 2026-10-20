"""LangGraph: score → draft → pending HITL. Approval happens in the UI, not in the model."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.scoring_engine import LeadInput, lead_score_to_dict, score_lead_rules

PROMPT = (ROOT / "mvp" / "prompts" / "qualify_and_draft_v1.md").read_text(encoding="utf-8")


class GraphState(TypedDict, total=False):
    lead: dict[str, Any]
    score: dict[str, Any]
    draft: str
    status: Literal["pending_approval", "approved", "rejected"]
    override_note: str


def node_score(state: GraphState) -> dict[str, Any]:
    lead = LeadInput.model_validate(state["lead"])
    return {"score": lead_score_to_dict(score_lead_rules(lead))}


def _template_draft(lead: dict[str, Any], score: dict[str, Any]) -> str:
    name_city = lead.get("city") or "a sua zona"
    band = score["band"]
    intent = score["intent"]
    if band == "HOT" and intent == "sell":
        return (
            f"Olá — obrigado pelo contacto. Somos a equipa de {name_city}. "
            "Gostávamos de agendar uma conversa hoje para perceber o imóvel e o prazo de venda. "
            "Pode indicar uma janela de 30 minutos ainda hoje ou amanhã? "
            "Não avançamos com anúncio nem avaliação formal sem a sua confirmação."
        )
    if band == "HOT":
        return (
            f"Olá — recebemos o seu pedido sobre {name_city}. "
            "Para não perder janelas de visita, pode falar connosco por telefone hoje? "
            "Indique três horários. Não reservamos visitas sem a sua confirmação expressa."
        )
    if band == "WARM":
        return (
            f"Olá — obrigado pelo interesse em {name_city}. "
            "Para o ajudar com calma, pode dizer-nos orçamento aproximado e prazo "
            "(já / 3 meses / 12 meses)? Depois um consultor responde com opções reais, sem inventar stock."
        )
    return (
        f"Olá — obrigado por escrever. Guardámos o seu contacto para {name_city}. "
        "Quando quiser avançar com compra, venda ou uma visita, responda a esta mensagem. "
        "Não faremos chamadas insistentes."
    )


def node_draft(state: GraphState) -> dict[str, Any]:
    lead = state["lead"]
    score = state["score"]
    draft = _template_draft(lead, score)
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key and not api_key.startswith("sk-your"):
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            payload = json.dumps({"lead": lead, "score": score}, ensure_ascii=False)
            response = client.chat.completions.create(
                model=model,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": payload},
                ],
            )
            text = (response.choices[0].message.content or "").strip()
            if text:
                draft = text
        except Exception:
            pass
    return {"draft": draft, "status": "pending_approval"}


def build_graph():
    graph = StateGraph(GraphState)
    # Node names must not collide with GraphState keys ("score", "draft").
    graph.add_node("score_lead", node_score)
    graph.add_node("write_draft", node_draft)
    graph.add_edge(START, "score_lead")
    graph.add_edge("score_lead", "write_draft")
    graph.add_edge("write_draft", END)
    return graph.compile()


LEAD_GRAPH = build_graph()
