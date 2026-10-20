"""Build the agent packet: score + rationale + matches + a draft the agent may send themselves."""

from __future__ import annotations

import re
import uuid

from .guardrail import check_fields
from .schema import AgentPacket, Band, Intent, Lead, LeadScore, ListingMatch, PacketStatus, SearchFilters
from .scoring import NEXT_ACTIONS

_PT_MARKERS = re.compile(r"\b(quero|procuro|olá|ola|obrigad[oa]|casa|comprar|vender|arrendar|orçamento|visita|imóvel|preços|sem)\b", re.IGNORECASE)

WITHHELD = "[draft withheld by the banned-attribute guardrail — agent must review manually]"


def is_portuguese(text: str) -> bool:
    return bool(_PT_MARKERS.search(text))


def _listing_lines(matches: list[ListingMatch]) -> list[str]:
    return [f"- {m.listing.title}: €{m.listing.price_eur:,}, {m.listing.area_m2} m² (ref {m.listing.listing_id})" for m in matches]


def draft_reply(lead: Lead, score: LeadScore, matches: list[ListingMatch]) -> str:
    pt = is_portuguese(lead.message)
    where = f" na zona de {lead.city}" if pt and lead.city else (f" in {lead.city}" if lead.city else "")
    n = len(matches)
    if score.next_action == NEXT_ACTIONS["email_only"]:
        return (f"Olá! Obrigado pelo contacto. Para o ajudar{where}, pode indicar-me o orçamento e quando pretende "
                "avançar? Se preferir, deixe-me um número de telefone e ligo-lhe." if pt else
                f"Hello, thanks for your enquiry. To help you{where}, could you share your budget and timing? "
                "If you prefer, leave a phone number and I will call you.")
    if score.band == Band.COLD:
        return ("(Sem resposta recomendada agora — lead em drip de baixa frequência.)" if pt
                else "(No reply recommended now — lead parked in a low-frequency drip.)")
    if score.intent == Intent.SELL:
        return (f"Olá! Obrigado pelo contacto. Posso marcar uma avaliação do seu imóvel{where} esta semana? "
                "Que dia e horário lhe dão mais jeito?" if pt else
                f"Hello, thanks for getting in touch. Could we book a valuation of your property{where} this week? "
                "Which day and time suit you best?")
    if matches:
        lines = "\n".join(_listing_lines(matches))
        if pt:
            what = "1 imóvel que corresponde" if n == 1 else f"{n} imóveis que correspondem"
            return (f"Olá! Obrigado pelo contacto. Selecionei {what} ao que procura{where}:\n"
                    f"{lines}\nQuando lhe dá jeito uma visita (presencial ou por videochamada)?")
        what = "is 1 property" if n == 1 else f"are {n} properties"
        verb = "matches" if n == 1 else "match"
        return (f"Hello, thanks for your enquiry. Here {what}{where} that {verb} what you described:\n"
                f"{lines}\nWhen would suit you for a viewing (in person or by video call)?")
    if pt:
        return (f"Olá! Obrigado pelo contacto. Para lhe enviar opções{where}, pode indicar-me o orçamento, "
                "a tipologia e quando pretende avançar?")
    return (f"Hello, thanks for your enquiry. To send you options{where}, could you share your budget, "
            "the typology you need and when you hope to move?")


def build_packet(lead: Lead, score: LeadScore, *, notes: list[str], filters: SearchFilters | None,
                 matches: list[ListingMatch]) -> AgentPacket:
    draft = draft_reply(lead, score, matches)
    guard = check_fields({
        "rationale": score.rationale,
        "next_action": score.next_action,
        "draft_reply_for_agent": draft,
        **{f"logistics_notes[{i}]": n for i, n in enumerate(notes)},
    })
    blocked = not guard.passed or score.used_banned_attribute
    return AgentPacket(
        packet_id="pkt_" + uuid.uuid4().hex[:12],
        lead=lead,
        score=score,
        logistics_notes=notes,
        filters_used=filters,
        matches=matches,
        draft_reply_for_agent=WITHHELD if blocked else draft,
        guardrail=guard,
        status=PacketStatus.BLOCKED_GUARDRAIL if blocked else PacketStatus.PENDING_REVIEW,
    )
