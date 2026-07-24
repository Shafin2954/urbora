# prices.md — every price the finance engine is allowed to use

This file is **the only source of money inputs** for `backend/finance/`. If a number
is not in a table below with a citation, the engine reports it unavailable rather than
guessing (CLAUDE.md §2.2, PRD §8 Tier0.5: *"every row cited or deleted"*).

It is parsed by `backend/finance/catalog.py`, so the table shapes matter:

- Columns are matched **by header name**, not position — you can reorder or add columns.
- A row with an empty price/cost cell is treated as **absent**, not as zero.
- `crop` must be one of the canonical keys: `boro_rice`, `aman_rice`, `potato`,
  `mustard`, `lentil`. Anything else is ignored with a warning.
- Money is BDT. Quantities are per hectare. Yields come from crop.db in kg/ha and are
  **not** in this file.

## Status: farm-gate + input costs filled (2026-07-24)

The yearbook extraction (`agristats.db`) landed and covers real, cited farm-gate prices
for all 5 crops and real cost-of-cultivation for boro/aman/potato. Mustard and lentil
have **zero** cost coverage in that database — their cost rows below are hand-curated
from BARC's Fertilizer Recommendation Guide (FRG-2024) and BARI's Krishi Projukti
Hatboi (real fertilizer doses, page-cited) priced against a dated government
fertiliser-price notice. Two honest limitations, stated plainly rather than hidden:

- **Mustard/lentil costs are fertiliser-only** (Urea/TSP/MoP) — seed cost and
  Gypsum/Zinc/Boron doses exist in the source PDFs but no citable Tk/kg price was found
  for any of them, so they are omitted rather than guessed. These two crops' costs are
  therefore a **minimum bound**, not a complete input cost, unlike boro/aman/potato
  (BBS's own published aggregate expenditure — complete).
- **The fertiliser price citation is dated 2023-04-11** — the most recent
  government-notified change found; no later revision was located. `confidence: low`
  on those six rows reflects that staleness.

---

## 1. Selling price — farm-gate (what the FARMER receives)

The engine reads **only this table** for revenue.

Basis must say what the price is *for*: paddy (unmilled) vs milled rice vs raw lentil
seed vs split dal are different commodities with different prices, and confusing them
is a 2x error in the farmer's favour.

Grade/variety choices, stated once here rather than repeated per row: Boro and Aman are
priced at the **Coarse** grade — the representative smallholder grade; Medium/Saru
(fine) grades exist in the source at a premium and were not used. Potato is the
**local** variety, not the Holland/Dutch premium variety. Lentil is `Lentil (Masur)`
specifically — **not** `Lentil (Motor)`, a different pulse (peas) present in the same
source table under a similar name.

| crop | price_bdt_per_kg | basis | source_id | source_title | locator | date | confidence |
|---|---|---|---|---|---|---|---|
| boro_rice | 30.51 | paddy, Coarse grade, harvest-time | agristats_bbs2025 | BBS Yearbook of Agricultural Statistics 2025 | Table 10.5.1 (Harvest-time market prices) p.638 | 2024-2025 | medium |
| aman_rice | 30.44 | paddy, Coarse grade, harvest-time | agristats_bbs2025 | BBS Yearbook of Agricultural Statistics 2025 | Table 10.5.1 (Harvest-time market prices) p.638 | 2024-2025 | medium |
| potato | 39.65 | local variety, harvest-time | agristats_bbs2025 | BBS Yearbook of Agricultural Statistics 2025 | Table 10.5.1 (Harvest-time market prices) p.638 | 2024-2025 | medium |
| mustard | 78.53 | harvest-time | agristats_bbs2025 | BBS Yearbook of Agricultural Statistics 2025 | Table 10.5.1 (Harvest-time market prices) p.638 | 2024-2025 | medium |
| lentil | 90.78 | Masur, raw seed, harvest-time | agristats_bbs2025 | BBS Yearbook of Agricultural Statistics 2025 | Table 10.5.1 (Harvest-time market prices) p.638 | 2024-2025 | medium |

## 2. Input costs — per hectare

One row per cost line per crop. `qty_per_ha × unit_cost_bdt` is what the farmer pays,
and the finance engine rounds and sums these exactly as displayed.

boro_rice/aman_rice/potato costs are BBS's own published **aggregate** expenditure per
acre (source table gives one total figure, not itemized inputs) — represented below as
one honestly-labeled lump-sum line rather than an invented itemized split. Converted
acre→ha by dividing by this project's exact `ACRE_HA = 0.40468564224`
(`backend/units.py`).

mustard/lentil have **zero** cost-of-cultivation coverage in `agristats.db` (only
Aus/Amon/Boro/Wheat/Maize/Potato/Onion/Jute are covered there). Sourced instead from
real, page-cited fertilizer doses in BARC's Fertilizer Recommendation Guide (FRG-2024)
and BARI's Krishi Projukti Hatboi — product-basis kg/ha, midpoint of the source's stated
range — priced against a dated government fertiliser-price notice (Urea/TSP/MoP only;
no Gypsum price found anywhere, so Gypsum/Zinc/Boron doses — which do exist in the
source — are not costed). **These two crops' costs are a fertiliser-only minimum bound,
not a complete input cost** — seed cost is not included (no citable seed price found).

| crop | item | qty_per_ha | unit | unit_cost_bdt | source_id | source_title | locator | date | confidence |
|---|---|---|---|---|---|---|---|---|---|
| boro_rice | Total cultivation cost (all inputs, BBS aggregate) | 1 | ha | 96022.68 | agristats_bbs2025 | BBS Yearbook of Agricultural Statistics 2025 | Table 8.4 (Productivity and expenditure of Boro by Division) p.540 | 2024-2025 | medium |
| aman_rice | Total cultivation cost (all inputs, BBS aggregate) | 1 | ha | 73286.51 | agristats_bbs2025 | BBS Yearbook of Agricultural Statistics 2025 | Table 8.3 (Productivity and expenditure of Amon by Division) p.539 | 2024-2025 | medium |
| potato | Total cultivation cost (all inputs, BBS aggregate) | 1 | ha | 157532.15 | agristats_bbs2025 | BBS Yearbook of Agricultural Statistics 2025 | Table 8.5 (Productivity and expenditure, Rabi crops incl. Potato) p.541 | 2024-2025 | medium |
| mustard | Urea (mid of 250–300 kg/ha range) | 275 | kg | 27 | bari_hatboi_frg_2024 | BARI Krishi Projukti Hatboi + BARC FRG-2024, priced via Daily Star fertiliser-price notice | Hatboi PDF p.140 (printed ~p.115); price: thedailystar.net "Fertiliser prices raised by Tk 5 per kg" | 2023-04-11 | low |
| mustard | TSP (mid of 170–180 kg/ha range) | 175 | kg | 27 | bari_hatboi_frg_2024 | BARI Krishi Projukti Hatboi + BARC FRG-2024, priced via Daily Star fertiliser-price notice | Hatboi PDF p.140 (printed ~p.115); same price source | 2023-04-11 | low |
| mustard | MoP (mid of 85–100 kg/ha range) | 92.5 | kg | 20 | bari_hatboi_frg_2024 | BARI Krishi Projukti Hatboi + BARC FRG-2024, priced via Daily Star fertiliser-price notice | Hatboi PDF p.140 (printed ~p.115); same price source | 2023-04-11 | low |
| lentil | Urea (mid of 40–45 kg/ha range) | 42.5 | kg | 27 | bari_hatboi_frg_2024 | BARI Krishi Projukti Hatboi + BARC FRG-2024, priced via Daily Star fertiliser-price notice | Hatboi PDF p.103 (printed ~p.78); same price source | 2023-04-11 | low |
| lentil | TSP (mid of 80–90 kg/ha range) | 85 | kg | 27 | bari_hatboi_frg_2024 | BARI Krishi Projukti Hatboi + BARC FRG-2024, priced via Daily Star fertiliser-price notice | Hatboi PDF p.103 (printed ~p.78); same price source | 2023-04-11 | low |
| lentil | MoP (mid of 40–45 kg/ha range) | 42.5 | kg | 20 | bari_hatboi_frg_2024 | BARI Krishi Projukti Hatboi + BARC FRG-2024, priced via Daily Star fertiliser-price notice | Hatboi PDF p.103 (printed ~p.78); same price source | 2023-04-11 | low |

## 3. Retail market context — NOT a farmer's selling price

Kept because PRD §8 Tier0.5 asks for a current, dated market bulletin, and because it
is genuinely useful for the farmer to see what their crop sells for in Dhaka. It is
**deliberately unreachable from the revenue path**: `catalog.py` never reads this table
into a projection.

The gap is not small. Coarse rice retails here at 50–60৳/kg, while a farmer sells
*paddy* — unmilled, and about 65% of it survives milling. Treating the retail number as
farm-gate would roughly double every revenue figure on screen.

Source for every row below: **Trading Corporation of Bangladesh (TCB), daily retail
price bulletin for Dhaka city, serial 180, memo 26.05.0000.017.31.01.26-587, dated
24-07-2026.** Markets surveyed: Sipahibagh, Mirpur-6, Mohammadpur Town Hall, New Market,
Rampura, Mohakhali. <https://www.tcb.gov.bd>

| commodity | related_crop | price_min_bdt_per_kg | price_max_bdt_per_kg | note |
|---|---|---|---|---|
| চাল সরু (নাজির/মিনিকেট) | boro_rice | 72 | 85 | milled fine rice, retail |
| চাল (মাঝারী) পাইজাম/আটাশ | boro_rice | 55 | 68 | milled medium rice, retail |
| চাল (মোটা)/স্বর্ণা/চায়না ইরি | aman_rice | 50 | 60 | milled coarse rice, retail |
| মশুর ডাল (বড় দানা) | lentil | 90 | 100 | split dal, retail — not raw lentil seed |
| আলু (নতুন/পুরাতন) | potato | 25 | 30 | retail |

Not in this bulletin: paddy, mustard, mustard oilseed. Their retail rows do not exist,
which is itself worth knowing — this source cannot cover the full crop set.

---

## Conventions

- **1 maund = 40 kg** (market/DAM maund, ratified — see `backend/units.py`). Prices
  quoted per maund must be divided by 40 before entering the table above.
- Prices move, so `confidence` for any market price is at most `medium` (PRD §7).
- `date` is the date the price refers to, not the date it was copied here.
