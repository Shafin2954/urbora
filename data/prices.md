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

## Why the farm-gate table is empty right now

The yearbook extraction is still running. Until its rows land, every crop reports
`price_unavailable`, the Profit component of the crop scorer stays off, and the finance
tool says so in Bangla instead of inventing a number. **Filling in a row is the only
action needed to switch all of that on** — no code change.

---

## 1. Selling price — farm-gate (what the FARMER receives)

The engine reads **only this table** for revenue.

Basis must say what the price is *for*: paddy (unmilled) vs milled rice vs raw lentil
seed vs split dal are different commodities with different prices, and confusing them
is a 2x error in the farmer's favour.

| crop | price_bdt_per_kg | basis | source_id | source_title | locator | date | confidence |
|---|---|---|---|---|---|---|---|

<!-- No rows yet. Pending: BBS Yearbook of Agricultural Statistics Ch.10, harvest-time
     and wholesale prices 2023-24, one row per crop, table + page cited.
     Example of a filled row, for format only — do not uncomment, it is not real:
     | boro_rice | 30.50 | paddy, harvest-time | bbs_yearbook_2024 | BBS Yearbook of Agricultural Statistics 2024 | Ch10 Table 10.3 p.512 | 2024-12-31 | medium | -->

## 2. Input costs — per hectare

One row per cost line per crop. `qty_per_ha × unit_cost_bdt` is what the farmer pays,
and the finance engine rounds and sums these exactly as displayed.

| crop | item | qty_per_ha | unit | unit_cost_bdt | source_id | source_title | locator | date | confidence |
|---|---|---|---|---|---|---|---|---|---|

<!-- No rows yet. Pending, per PRD §8 Tier0.5 and NOTES #18:
     - seed rates and fertilizer doses: BARC Fertilizer Recommendation Guide (FRG-2018),
       dose table by crop x soil fertility class, page-cited
     - fertilizer prices: BADC/DAE published rates, URL + date
     - labour: BBS Yearbook Ch.7.5 agricultural wage table, page-cited
     Every row needs a real locator. A row without one must be deleted, not estimated. -->

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
