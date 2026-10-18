"""Create a synthetic but realistic SME-agency lead table for Portugal.

No live personal data. Names are fictional. Cities follow INE demand geography.
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

CITIES = [
    ("Lisboa", 0.28),
    ("Porto", 0.16),
    ("Cascais", 0.08),
    ("Setúbal", 0.07),
    ("Braga", 0.06),
    ("Coimbra", 0.05),
    ("Faro", 0.06),
    ("Oeiras", 0.06),
    ("Sintra", 0.08),
    ("Vila Nova de Gaia", 0.10),
]

CHANNELS = ["website", "idealista", "imovirtual", "referral", "walk-in", "instagram"]

BUY_MSGS = [
    "Quero comprar T2 em {city}, orçamento definido, posso visitar esta semana.",
    "Procuro casa para viver em {city}. Já vi várias e quero avançar com crédito habitação.",
    "Interested in buying near {city}. Budget is ready. Can we book a viewing?",
    "Estou a comparar 4 T3 em {city} e gostava de uma proposta esta quinzena.",
]
SELL_MSGS = [
    "Quero vender o meu T3 em {city} e preciso de uma avaliação esta semana.",
    "Herdámos um apartamento em {city} e queremos listar o mais rápido possível.",
    "Thinking of selling in {city} in the next two months. What is the process?",
]
RENT_MSGS = [
    "Procuro arrendamento em {city} para 12 meses, estudante.",
    "Looking to rent a studio in {city}, no rush.",
]
COLD_MSGS = [
    "Só a ver preços em {city}, sem pressa e sem orçamento.",
    "Just looking at the market in {city} for curiosity.",
    "Crypto investment opportunity in {city} real estate guaranteed profit.",
]
WARM_MSGS = [
    "Talvez compre em {city} no próximo ano, ainda a ver opções.",
    "Quero comprar em {city} mas o crédito ainda não está aprovado.",
    "Gostava de vender em {city} daqui a uns 8 meses, podem contactar-me por email.",
]


def _pick_city() -> str:
    names, weights = zip(*CITIES)
    return random.choices(list(names), weights=list(weights), k=1)[0]


def build_rows(n: int = 180, seed: int = 42) -> list[dict]:
    random.seed(seed)
    rows: list[dict] = []
    for i in range(1, n + 1):
        city = _pick_city()
        roll = random.random()
        if roll < 0.18:
            family, message_pool, intent = "hot_buy", BUY_MSGS, "buy"
            budget = random.choice([220_000, 280_000, 350_000, 480_000, 650_000])
            timeline = random.choice([14, 30, 45, 60])
            views, saved = random.randint(8, 22), random.randint(3, 8)
            phone, replied = True, random.choice([True, False])
        elif roll < 0.30:
            family, message_pool, intent = "hot_sell", SELL_MSGS, "sell"
            budget = None
            timeline = random.choice([21, 45, 75])
            views, saved = random.randint(0, 4), 0
            phone, replied = True, True
        elif roll < 0.55:
            family, message_pool, intent = "warm", WARM_MSGS, "buy"
            budget = random.choice([None, 200_000, 300_000])
            timeline = random.choice([120, 180, 270, None])
            views, saved = random.randint(2, 7), random.randint(0, 2)
            phone, replied = random.choice([True, False]), False
        elif roll < 0.70:
            family, message_pool, intent = "rent", RENT_MSGS, "rent"
            budget = random.choice([750, 900, 1200])
            timeline = random.choice([30, 90, 180])
            views, saved = random.randint(1, 6), random.randint(0, 2)
            phone, replied = False, False
        else:
            family, message_pool, intent = "cold", COLD_MSGS, "unknown"
            budget = None
            timeline = None
            views, saved = random.randint(0, 2), 0
            phone, replied = False, False

        rows.append(
            {
                "lead_id": f"lead_{i:04d}",
                "channel": random.choice(CHANNELS),
                "city": city,
                "message": random.choice(message_pool).format(city=city),
                "budget_eur": budget if budget is not None else "",
                "timeline_days": timeline if timeline is not None else "",
                "property_views_7d": views,
                "saved_listings": saved,
                "replied_to_agent": replied,
                "phone_provided": phone,
                "email_provided": True,
                "synthetic_family": family,
                "synthetic_intent_hint": intent,
            }
        )
    return rows


EVAL_CASES = [
    {
        "lead_id": "eval_01",
        "channel": "website",
        "city": "Lisboa",
        "message": "Quero comprar T2 em Lisboa. Orçamento 380 mil. Posso visitar amanhã à tarde.",
        "budget_eur": 380000,
        "timeline_days": 21,
        "property_views_7d": 12,
        "saved_listings": 4,
        "replied_to_agent": True,
        "phone_provided": True,
        "email_provided": True,
        "expected_band": "HOT",
        "expected_intent": "buy",
        "notes": "Clear buy intent, budget, near-term visit, contactable.",
    },
    {
        "lead_id": "eval_02",
        "channel": "referral",
        "city": "Porto",
        "message": "Quero vender o meu T3 no Porto e preciso de avaliação esta semana.",
        "budget_eur": None,
        "timeline_days": 30,
        "property_views_7d": 1,
        "saved_listings": 0,
        "replied_to_agent": True,
        "phone_provided": True,
        "email_provided": True,
        "expected_band": "HOT",
        "expected_intent": "sell",
        "notes": "Motivated seller; budget field unused on purpose.",
    },
    {
        "lead_id": "eval_03",
        "channel": "idealista",
        "city": "Braga",
        "message": "Talvez compre em Braga no próximo ano, ainda a ver opções.",
        "budget_eur": 250000,
        "timeline_days": 300,
        "property_views_7d": 4,
        "saved_listings": 1,
        "replied_to_agent": False,
        "phone_provided": False,
        "email_provided": True,
        "expected_band": "WARM",
        "expected_intent": "buy",
        "notes": "Real interest but slow timeline and weak contactability.",
    },
    {
        "lead_id": "eval_04",
        "channel": "instagram",
        "city": "Faro",
        "message": "Só a ver preços em Faro, sem pressa e sem orçamento.",
        "budget_eur": None,
        "timeline_days": None,
        "property_views_7d": 1,
        "saved_listings": 0,
        "replied_to_agent": False,
        "phone_provided": False,
        "email_provided": True,
        "expected_band": "COLD",
        "expected_intent": "unknown",
        "notes": "Browsing signal.",
    },
    {
        "lead_id": "eval_05",
        "channel": "website",
        "city": "Coimbra",
        "message": "Procuro arrendamento em Coimbra para 12 meses, estudante.",
        "budget_eur": 800,
        "timeline_days": 60,
        "property_views_7d": 3,
        "saved_listings": 1,
        "replied_to_agent": False,
        "phone_provided": False,
        "email_provided": True,
        "expected_band": "COLD",
        "expected_intent": "rent",
        "notes": "Rent is out of the sales-led SME sweet spot — park, do not rush-call.",
    },
    {
        "lead_id": "eval_06",
        "channel": "imovirtual",
        "city": "Lisboa",
        "message": "Crypto investment opportunity in Lisboa real estate guaranteed profit.",
        "budget_eur": None,
        "timeline_days": None,
        "property_views_7d": 0,
        "saved_listings": 0,
        "replied_to_agent": False,
        "phone_provided": False,
        "email_provided": True,
        "expected_band": "COLD",
        "expected_intent": "unknown",
        "notes": "Spam. Must not be treated as a hot investor.",
    },
    {
        "lead_id": "eval_07",
        "channel": "website",
        "city": "Cascais",
        "message": "Family from abroad wants to buy in Cascais. Budget ready. Viewing this month.",
        "budget_eur": 720000,
        "timeline_days": 25,
        "property_views_7d": 9,
        "saved_listings": 5,
        "replied_to_agent": False,
        "phone_provided": True,
        "email_provided": True,
        "expected_band": "HOT",
        "expected_intent": "buy",
        "notes": "Nationality must not appear in the rationale even if the message mentions abroad.",
    },
]


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    csv_path = DATA / "synthetic_leads.csv"
    fieldnames = list(rows[0].keys())
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    eval_path = DATA / "eval_cases.jsonl"
    with eval_path.open("w", encoding="utf-8") as handle:
        for case in EVAL_CASES:
            handle.write(json.dumps(case, ensure_ascii=False) + "\n")

    notes = DATA / "data_notes.md"
    notes.write_text(
        """# Data notes

`synthetic_leads.csv` is **not** a live CRM extract. It is generated by `generate_leads.py`
to resemble portal and website enquiries an SME Portuguese agency might see.

Public market context (not in this CSV) comes from Statistics Portugal (INE) House Price
Index and median €/m² releases for 2025 and Q1 2026. See `research/sector_research.md`.

Personal fields are fictional. Do not treat `lead_*` IDs as real people.
""",
        encoding="utf-8",
    )
    print(f"Wrote {csv_path} ({len(rows)} rows) and {eval_path}")


if __name__ == "__main__":
    main()
