# Sector research — Portuguese SME residential estate agencies

**Client sketch:** Chleo is CEO of a fictional independent agency with 10–50 people and 2–5 offices in Portugal. Typical mix: a Lisbon or Porto flagship plus suburban/coastal branches. Revenue is commission on sales, with some lettings. Lead intake is portal-heavy (Idealista, Imovirtual), website forms, referrals, and walk-ins.

**Company-size implication:** there is no data science team, no CRM scientist, and no in-house MLOps. A useful AI tool must be runnable by an operations manager, inspectable by the CEO, and cheap enough that a missed month of commissions is the bigger risk — not the software bill.

## What is happening in the market (public sources)

Figures below are from **Statistics Portugal (INE)** House Price Index and dwelling-transaction statistics. They are **national market context**, not Chleo’s private books.

| Signal | Figure | Why it matters to an SME agency | Source |
| --- | --- | --- | --- |
| House prices, 2025 | HPI **+17.6%** year; existing dwellings **+18.9%**, new **+14.2%** | Fast price moves mean stale valuations and “window shoppers” who cannot actually buy | [INE, 2025 HPI](https://www.ine.pt/ngt_server/attachfileu.jsp?att_display=n&att_download=y&look_parentBoui=782896855) |
| Transactions, 2025 | **169,812** dwellings; volume **+8.6%** vs 2024 | More deals nationally, but also more portal noise at branch level | Same INE 2025 HPI note |
| Q1 2026 prices vs activity | HPI **+17.8%** YoY; transactions **−8.7%** to **37,745** | Prices still rising while **fewer** sales close — agents waste time on leads that will not transact | [INE, Q1 2026 HPI](https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_destaques&DESTAQUESdest_boui=770297229&DESTAQUESmodo=2) |
| Q1 2026 value vs volume | Transaction **value** **€9.9bn** (**+3.2%** YoY) even as unit volume fell | Mix shifts toward higher-value stock; qualification of budget/timing becomes more valuable | Same |
| Non-resident buyers, Q1 2026 | **1,770** purchases, **−15.6%** YoY | Cross-border demand is real but **cooling**; treating every “from abroad” message as VIP is a bias risk | Same |
| Median €/m² (12 months to Mar 2026) | Portugal **€2,168/m²**; Grande Lisboa **€3,598**; AMP **€2,404**; Algarve **€3,240** | Branch mix (Lisboa vs Braga vs Faro) changes what “hot budget” means | [INE, municipal prices Q1 2026](https://www.ine.pt/ngt_server/attachfileu.jsp?att_display=n&att_download=y&look_parentBoui=804180659) |
| Peak municipalities (Q1 2026 quarter) | Lisboa **€5,292/m²**; Cascais **€5,000**; Oeiras **€4,511** | A 5-office SME that covers Lisboa *and* a secondary city cannot use one national threshold | [INE PT release](https://www.ine.pt/ngt_server/attachfileu.jsp?att_display=n&att_download=y&look_parentBoui=804178838) |
| 2025 regional value share | Grande Lisboa **30.1%** of transaction **value** (share falling); Norte **25.6%** (share rising) | Opportunity is not only Lisbon; Porto/Norte is a growth story for mid-size independents | INE 2025 HPI note |

**Read for Chleo in one sentence:** the market is still expensive and geographically concentrated, but **unit sales cooled in early 2026**. That is exactly when undifferentiated “call every portal lead” stops working.

## How SME agencies actually work (process, not hype)

1. Portals generate high-volume, low-context enquiries (“info please”).
2. A receptionist or junior agent triages into a CRM (many still use Excel + WhatsApp).
3. Senior agents cherry-pick names they recognise; new leads wait.
4. Speed-to-lead is the unglamorous conversion driver; after a few hours the buyer has already booked with a competitor.
5. Compliance (RGPD, AML/KYC at offer stage, energy certificates, simple urban licensing questions) sits on the same people who are supposed to be selling.

Industry associations such as **APEMIP** and **AMI** describe a fragmented agency landscape: many micro-brands, a few large networks (Remax, Era, Kw, Century 21). Chleo’s firm is the messy middle — big enough to have process pain, small enough that a €40k platform deal will be rejected.

## Data used in this project

| Dataset | Type | Use |
| --- | --- | --- |
| INE HPI and median prices | Public official statistics | Charts and narrative; not used to train a model |
| `data/synthetic_leads.csv` | Synthetic CRM-like table (180 rows) | Volume, geography, intent mix, capacity story |
| `data/eval_cases.jsonl` | Hand-authored golden cases | Round 1 scored mini-set |

**No live personal data.** Portal terms of use also make scraping client inboxes a legal and contractual dead end.

## What “the AI” means in this engagement

Not a chatbot on the public website as the first move. For this SME, “the AI” is a **triage assistant**: it reads an enquiry plus a few behavioural fields, returns HOT/WARM/COLD with a reason an agent can disagree with, and suggests the next human action. Sending messages to consumers stays with the licensed agent.

## Sources

- Statistics Portugal (INE), House Price Index 2025 annual note: https://www.ine.pt/ngt_server/attachfileu.jsp?att_display=n&att_download=y&look_parentBoui=782896855
- INE, HPI 1st quarter 2026 highlight: https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_destaques&DESTAQUESdest_boui=770297229&DESTAQUESmodo=2
- INE, municipal / NUTS 3 median prices Q1 2026: https://www.ine.pt/ngt_server/attachfileu.jsp?att_display=n&att_download=y&look_parentBoui=804180659
- Comissão Nacional de Proteção de Dados (CNPD) — RGPD guidance for Portuguese organisations: https://www.cnpd.pt/
- EU AI Act overview (European Commission): https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai
