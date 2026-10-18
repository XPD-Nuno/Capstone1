"""CEO-facing charts. One message per figure. Synthetic CRM + INE context."""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.scoring_engine import LeadInput, score_lead_rules

CHARTS = ROOT / "charts"
DATA = ROOT / "data" / "synthetic_leads.csv"

plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
    }
)

COLOURS = {
    "HOT": "#1B6B4A",
    "WARM": "#C47B17",
    "COLD": "#7A8699",
    "navy": "#1F3A5F",
    "teal": "#2A9D8F",
}


def load_scored():
    with DATA.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    scored = []
    for row in rows:
        lead = LeadInput(
            lead_id=row["lead_id"],
            channel=row["channel"],
            city=row["city"],
            message=row["message"],
            budget_eur=int(row["budget_eur"]) if row["budget_eur"] else None,
            timeline_days=int(row["timeline_days"]) if row["timeline_days"] else None,
            property_views_7d=int(row["property_views_7d"]),
            saved_listings=int(row["saved_listings"]),
            replied_to_agent=row["replied_to_agent"].lower() == "true",
            phone_provided=row["phone_provided"].lower() == "true",
        )
        score = score_lead_rules(lead)
        scored.append((row, score))
    return scored


def save(fig, name: str) -> None:
    path = CHARTS / name
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


def chart_capacity(scored) -> None:
    n = len(scored)
    agents = 8
    sustainable = agents * 6  # serious conversations / day
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    ax.bar(["Weekly enquiries (synthetic week)", "What 8 agents can work well"], [n, sustainable * 5], color=[COLOURS["navy"], COLOURS["teal"]])
    ax.set_ylabel("Leads")
    ax.set_title("Chleo's problem is not 'more leads'. It is too many for the bench.")
    ax.text(0, n + 3, f"{n} raw enquiries", ha="center")
    ax.text(1, sustainable * 5 + 3, f"{sustainable * 5} quality slots / week", ha="center")
    save(fig, "01_capacity_gap.png")


def chart_bands(scored) -> None:
    bands = Counter(s.band.value for _, s in scored)
    order = ["HOT", "WARM", "COLD"]
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    vals = [bands[b] for b in order]
    ax.bar(order, vals, color=[COLOURS[b] for b in order])
    ax.set_ylabel("Leads")
    ax.set_title("Most enquiries should not get a senior agent's first hour.")
    for i, v in enumerate(vals):
        ax.text(i, v + 1, str(v), ha="center")
    save(fig, "02_band_mix.png")


def chart_intent(scored) -> None:
    intents = Counter(s.intent.value for _, s in scored)
    labels = ["buy", "sell", "rent", "unknown"]
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    ax.bar(labels, [intents[k] for k in labels], color=COLOURS["navy"])
    ax.set_title("Sales-led SME: buy and sell pay the rent. Rent and 'unknown' clog the queue.")
    save(fig, "03_intent_mix.png")


def chart_geo(scored) -> None:
    cities = Counter(row["city"] for row, _ in scored)
    top = cities.most_common(8)
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.barh([c for c, _ in reversed(top)], [n for _, n in reversed(top)], color=COLOURS["teal"])
    ax.set_title("Leads cluster where prices are hottest — Lisboa/Porto first, not 'all Portugal'.")
    save(fig, "04_geography.png")


def chart_delay_cost(scored) -> None:
    """Illustrative cost of delay using assumed conversion rates by band (labelled as assumptions)."""
    bands = Counter(s.band.value for _, s in scored)
    # Assumption: commission 15k on a completed deal; conversion if contacted <1h vs >8h
    conversion_fast = {"HOT": 0.18, "WARM": 0.06, "COLD": 0.01}
    conversion_slow = {"HOT": 0.08, "WARM": 0.04, "COLD": 0.01}
    commission = 12_000
    fast = sum(bands[b] * conversion_fast[b] * commission for b in bands)
    slow = sum(bands[b] * conversion_slow[b] * commission for b in bands)
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    ax.bar(["Contact HOT leads in <1 hour", "Same mix, first touch after 8 hours"], [fast, slow], color=[COLOURS["HOT"], COLOURS["COLD"]])
    ax.set_ylabel("Illustrative expected commission (€)")
    ax.set_title("Delay is a revenue leak. Assumptions are in charts_documentation.md.")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))
    save(fig, "05_delay_cost.png")
    CHARTS.joinpath("05_delay_cost_numbers.txt").write_text(
        f"fast_eur={fast:.0f}\nslow_eur={slow:.0f}\ngap_eur={fast-slow:.0f}\n",
        encoding="utf-8",
    )


def chart_risk_opportunity() -> None:
    items = [
        ("UC1 scoring", 5, 4),
        ("UC2 drafts", 4, 3),
        ("UC3 briefing", 3, 2),
        ("AVM (out)", 2, 5),
    ]
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    ax.scatter([r for _, o, r in items], [o for _, o, r in items], s=280, c=[COLOURS["navy"], COLOURS["teal"], COLOURS["WARM"], "#9B2226"])
    for name, o, r in items:
        ax.annotate(name, (r, o), textcoords="offset points", xytext=(8, 4))
    ax.set_xlim(0.5, 5.5)
    ax.set_ylim(0.5, 5.5)
    ax.set_xlabel("Governance risk if built naively (1–5)")
    ax.set_ylabel("Opportunity for this SME (1–5)")
    ax.set_title("Start where value is high and risk is controllable with HITL — not AVM.")
    ax.axvline(3.5, color="#cccccc", linestyle="--", linewidth=1)
    ax.axhline(3.5, color="#cccccc", linestyle="--", linewidth=1)
    save(fig, "06_opportunity_risk.png")


def chart_ine_context() -> None:
    """Public INE context: 2025 boom vs Q1 2026 volume drop. Not Chleo's CRM."""
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    labels = ["2025 HPI\nvs 2024", "2025 transactions\nvs 2024", "Q1 2026 HPI\nvs Q1 2025", "Q1 2026 transactions\nvs Q1 2025"]
    vals = [17.6, 8.6, 17.8, -8.7]
    colors = [COLOURS["HOT"] if v > 0 else "#9B2226" for v in vals]
    ax.bar(labels, vals, color=colors)
    ax.axhline(0, color="#333", linewidth=0.8)
    ax.set_ylabel("Year-on-year change (%)")
    ax.set_title("Portugal 2026: prices still up, sales counts down — qualify harder, don't shout louder.")
    save(fig, "00_ine_market.png")


def main() -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    scored = load_scored()
    chart_ine_context()
    chart_capacity(scored)
    chart_bands(scored)
    chart_intent(scored)
    chart_geo(scored)
    chart_delay_cost(scored)
    chart_risk_opportunity()
    print(f"scored {len(scored)} synthetic leads")


if __name__ == "__main__":
    main()
