"""Market price intelligence — docs/product/competition.md Tier 2.

    "Current and historical prices, plus a sell-now/store/wait recommendation
     with reasoning."

Every number here comes from `agristats.db :: fact_prices` (view `v_prices`) —
83,097 BBS Yearbook rows already in this repo, monthly, 2007-08 to 2025. Nothing
is fetched live and nothing is invented.

Three honesty constraints are built into the shape of the output, not bolted on
as a disclaimer:

1. **This is a seasonal PATTERN, not a forecast.** We report what prices have
   historically done between month X and month Y, averaged across the years in
   the source. Exactly the discipline weather.py applies to climatology: an
   average that may differ, never a prediction. `basis: "historical_pattern"`
   travels with the payload so the agent cannot quietly promote it.

2. **These are WHOLESALE prices, not what the farmer is paid.** Revenue in this
   project comes only from the cited farm-gate table in data/prices.md
   (backend/finance/catalog.py), and this module is deliberately not reachable
   from that path. The wholesale series is the right shape for *timing* — it is
   the one that shows month-to-month movement — but using its level as income
   would overstate every projection.

3. **Storage cost and storage loss are unknown.** No source in this project
   prices a cold store or quantifies spoilage, so a "wait" reading names the
   historical upside and says the carrying cost is unaccounted. A farmer
   deciding to hold potatoes for four months needs to weigh a real storage bill
   we cannot quote.

Commodity choice mirrors data/prices.md's conventions exactly, so the two tables
are talking about the same thing: paddy (unmilled) at Coarse grade rather than
milled rice, potato at the local variety rather than Holland, mustard as the
oilSEED rather than the oil, lentil as raw Masur rather than split dal.
"""

from __future__ import annotations

import sqlite3
import statistics
from datetime import datetime, timezone
from pathlib import Path

_DB = Path(__file__).resolve().parents[2] / "data" / "agristats.db"

# canonical crop -> (commodity rows in v_prices, what the row is a price FOR)
_COMMODITY: dict[str, tuple[tuple[str, ...], str]] = {
    "boro_rice": (("Paddy Boro Coarse", "Paddy Boro coarse"), "paddy (unmilled), Coarse grade"),
    "aman_rice": (("Paddy Aman Coarse", "Paddy Aman coarse"), "paddy (unmilled), Coarse grade"),
    "potato": (("Vegetable Potato: Local", "Vegetable Potato : Local", "Potato (local)"), "local variety potato"),
    "mustard": (("Oil seed Mustard", "Oil Seed Mustard"), "mustard oilseed (not mustard oil)"),
    "lentil": (("Pulses Masur", "Lentil (Masur)"), "raw Masur lentil seed (not split dal)"),
}

_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

# Below this, a later month's advantage is noise in a multi-year average rather
# than a reason to carry a crop for months.
_MEANINGFUL_GAIN_PCT = 5.0

_QUINTAL_KG = 100.0


def _rows(commodities: tuple[str, ...]) -> list[tuple[str, float, str]]:
    if not _DB.exists():
        return []
    placeholders = ",".join("?" for _ in commodities)
    sql = (
        f"SELECT period, price_taka, reference_year FROM v_prices "
        f"WHERE commodity IN ({placeholders}) "
        f"  AND price_type = 'wholesale' "
        f"  AND period IS NOT NULL AND period <> 'Average' "
        f"  AND price_taka IS NOT NULL AND price_taka_is_outlier = 0"
    )
    # Read-only: this database is source data and nothing here may write to it.
    with sqlite3.connect(f"file:{_DB}?mode=ro", uri=True) as conn:
        return list(conn.execute(sql, commodities))


def market_price(crop: str, month: int | None = None) -> dict:
    """Seasonal price pattern for one crop, plus a sell / store reading.

    `month` (1-12) is the month the farmer is deciding in; it defaults to the
    current month. The reading compares that month's historical average against
    the following months of the same year.
    """
    entry = _COMMODITY.get(crop)
    if entry is None:
        return {
            "error": "unsupported_crop",
            "crop": crop,
            "supported": sorted(_COMMODITY),
            "degraded": "তথ্য যথেষ্ট নয়",
        }
    commodities, basis = entry

    raw = _rows(commodities)
    if not raw:
        return {
            "error": "price_history_unavailable",
            "crop": crop,
            "message_bn": "এই ফসলের ঐতিহাসিক বাজারদর পাওয়া যায়নি।",
            "degraded": "তথ্য যথেষ্ট নয়",
        }

    by_month: dict[str, list[float]] = {name: [] for name in _MONTHS}
    years: set[str] = set()
    for period, price, year in raw:
        if period in by_month:
            by_month[period].append(float(price) / _QUINTAL_KG)  # Taka/quintal -> Tk/kg
            years.add(str(year))

    curve = [
        {
            "month": index + 1,
            "month_name": name,
            "avg_price_bdt_per_kg": round(statistics.mean(values), 2) if values else None,
            "observations": len(values),
        }
        for index, name in enumerate(_MONTHS)
        for values in [by_month[name]]
    ]

    now_month = month or datetime.now(timezone.utc).month
    current = curve[now_month - 1]

    # Only the rest of the same year: a "wait" that means "hold it for eleven
    # months" is not a harvest-timing decision, it is a different business.
    later = [row for row in curve[now_month:] if row["avg_price_bdt_per_kg"] is not None]
    best = max(later, key=lambda row: row["avg_price_bdt_per_kg"], default=None)

    verdict = "unknown"
    gain_pct = None
    reason_bn = "তুলনা করার মতো যথেষ্ট তথ্য নেই।"

    if current["avg_price_bdt_per_kg"] is None:
        reason_bn = "এই মাসের ঐতিহাসিক গড় দাম পাওয়া যায়নি।"
    elif best is None:
        verdict = "sell_now"
        reason_bn = "বছরের বাকি মাসগুলোর তুলনামূলক তথ্য নেই, তাই অপেক্ষার যুক্তি দেখানো যাচ্ছে না।"
    else:
        gain_pct = round(
            (best["avg_price_bdt_per_kg"] - current["avg_price_bdt_per_kg"])
            / current["avg_price_bdt_per_kg"] * 100, 1
        )
        if gain_pct >= _MEANINGFUL_GAIN_PCT:
            verdict = "consider_storing"
            reason_bn = (
                f"গত বছরগুলোতে {current['month_name']} মাসের তুলনায় "
                f"{best['month_name']} মাসে গড় দাম {gain_pct}% বেশি ছিল। "
                "এটি অতীতের ধারা, ভবিষ্যতের নিশ্চয়তা নয় — এবং সংরক্ষণের খরচ ও "
                "ক্ষতি এই হিসাবে ধরা হয়নি।"
            )
        else:
            verdict = "sell_now"
            reason_bn = (
                f"গত বছরগুলোতে {current['month_name']} মাসের পর দাম উল্লেখযোগ্যভাবে "
                f"বাড়েনি (সর্বোচ্চ {gain_pct}%), তাই ধরে রাখার সুবিধা কম।"
            )

    return {
        "crop": crop,
        "commodity": commodities[0],
        "price_basis": basis,
        "price_type": "wholesale",
        # Said twice on purpose — once as a flag the agent can branch on, once
        # as prose it can read to the farmer.
        "basis": "historical_pattern",
        "not_a_forecast": True,
        "is_farm_gate": False,
        "farm_gate_note_en": (
            "Wholesale market prices, NOT what the farmer is paid. Revenue "
            "figures come from the cited farm-gate table in data/prices.md."
        ),
        "storage_cost_bdt": None,
        "storage_cost_note_bn": "সংরক্ষণের খরচ ও ক্ষতির নির্ভরযোগ্য তথ্য আমাদের উৎসে নেই।",
        "decision_month": now_month,
        "current_month_avg_bdt_per_kg": current["avg_price_bdt_per_kg"],
        "best_later_month": best["month_name"] if best else None,
        "best_later_month_avg_bdt_per_kg": best["avg_price_bdt_per_kg"] if best else None,
        "expected_gain_pct": gain_pct,
        "verdict": verdict,
        "reason_bn": reason_bn,
        "monthly_curve": curve,
        "years_covered": f"{min(years)}–{max(years)}" if years else None,
        "observations": len(raw),
        "provenance": {
            "source_type": "dataset",
            "source_id": "agristats_bbs:fact_prices",
            "source_title": "BBS Yearbook of Agricultural Statistics — monthly wholesale prices",
            "locator": "agristats.db :: v_prices (price_type='wholesale')",
            "formula": (
                "mean of monthly wholesale Taka/Quintal / 100 -> Tk/kg, averaged "
                f"across {len(years)} reference years; outlier-flagged rows excluded"
            ),
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "confidence": "medium",
        },
    }
