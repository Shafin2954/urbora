"""Pest and disease risk — competition.md Tier 1 item 4.

    "Predict likely pests and diseases from crop, growth stage, and weather,
     with preventive and treatment options and estimated cost."

Deterministic, like every other number-producing tool here (CLAUDE.md rule 1):
the model calls this and narrates it. It never decides that blight is likely.

Three inputs decide a risk, and all three are real:

  growth stage   days after sowing, from the farmer's confirmed planting date
                 (the saved plan, or a date they state). Stage windows below are
                 the same day-offsets, from the same cited sources, that
                 season_plan.py already uses for its pest checkpoints — this
                 tool is the *live* half of those static checkpoints.
  weather        the live 16-day Open-Meteo forecast, including daily mean
                 relative humidity. Leaf-wetness diseases key on humidity, not
                 on rainfall totals.
  agronomy       the treatment text and doses come verbatim from the curated
                 KB passage named on each rule (data/kb/corpus.json), so every
                 recommendation carries the citation the passage carries.

What this tool deliberately does NOT do
---------------------------------------
It does not price the treatment. Tier 1 asks for an estimated cost and we have
the doses, but there is no citable Tk/kg price for any pesticide or fungicide in
any source this project holds: data/prices.md has no pesticide rows, and
agristats.db's fact_pesticides is national consumption tonnage, not price. Under
CLAUDE.md rule 2 an uncited price is a fabrication, so every risk reports
`treatment_cost_bdt: None` with `treatment_cost_note` saying why. Do not "fix"
this by estimating — fix it by finding a citable price list.

It also does not extrapolate past the forecast horizon. A rule whose stage
window starts after the last forecast day is reported as `upcoming` with no risk
level, because scoring it would mean inventing month-3 weather (NOTES #1).
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .districts import lookup_district
from .weather import get_forecast
from ..memory.store import get_farm, get_plan

_CORPUS_PATH = Path(__file__).resolve().parents[2] / "data" / "kb" / "corpus.json"

# ─────────────────────────────────────────────────────────────────────────────
# Rules
#
# One row per pest/disease we hold a cited KB passage for. `kb_id` is the
# passage in data/kb/corpus.json that supplies the treatment text — a rule
# without one would be advice we cannot source, so there are none.
#
# `stage`      inclusive days-after-sowing window in which the crop is
#              susceptible. Same offsets as season_plan.py's pest_checkpoint
#              rows, widened to a window because risk is not a single day.
# `temp_c`     (low, high) daily-mean-ish band that favours the organism,
#              evaluated against each forecast day's tmax/tmin midpoint.
# `humidity`   minimum daily mean RH% that favours it, or None if the organism
#              is not humidity-driven (aphids prefer dry, see `prefers_dry`).
# `wet_days`   (medium, high) thresholds: how many forecast days inside the
#              stage window must match before the risk is medium / high.
# ─────────────────────────────────────────────────────────────────────────────
_RULES: dict[str, tuple[dict[str, Any], ...]] = {
    "potato": (
        {
            "key": "late_blight",
            "name_bn": "নাবী ধ্বসা (লেট ব্লাইট)",
            "name_en": "Late blight",
            "scientific": "Phytophthora infestans",
            "kind": "disease",
            "kb_id": "potato_disease_blight",
            "stage": (30, 75),
            "temp_c": (12.0, 22.0),
            "humidity": 85.0,
            "prefers_dry": False,
            "wet_days": (2, 4),
            "why_bn": "ঠান্ডা ও স্যাঁতসেঁতে আবহাওয়ায় নাবী ধ্বসা দ্রুত ছড়ায়।",
        },
        {
            "key": "aphid",
            "name_bn": "জাব পোকা (এফিড)",
            "name_en": "Aphid",
            "scientific": "Myzus persicae",
            "kind": "pest",
            "kb_id": "potato_pest_aphid",
            "stage": (25, 70),
            "temp_c": (15.0, 25.0),
            "humidity": None,
            "prefers_dry": True,
            "wet_days": (3, 6),
            "why_bn": "শুষ্ক ও মৃদু উষ্ণ আবহাওয়ায় জাব পোকা বাড়ে, যা ভাইরাসও ছড়ায়।",
        },
    ),
    "mustard": (
        {
            "key": "alternaria",
            "name_bn": "অল্টারনারিয়া ব্লাইট",
            "name_en": "Alternaria blight",
            "scientific": "Alternaria brassicae",
            "kind": "disease",
            "kb_id": "mustard_disease_alternaria",
            "stage": (35, 75),
            "temp_c": (18.0, 27.0),
            "humidity": 80.0,
            "prefers_dry": False,
            "wet_days": (2, 4),
            "why_bn": "আর্দ্র আবহাওয়ায় পাতায় অল্টারনারিয়ার দাগ দ্রুত বাড়ে।",
        },
        {
            "key": "aphid",
            "name_bn": "জাব পোকা (এফিড)",
            "name_en": "Mustard aphid",
            "scientific": "Lipaphis erysimi",
            "kind": "pest",
            "kb_id": "mustard_pest_aphid",
            "stage": (45, 85),
            "temp_c": (15.0, 25.0),
            "humidity": None,
            "prefers_dry": True,
            "wet_days": (3, 6),
            "why_bn": "ফুল আসার সময় শুষ্ক ও মৃদু আবহাওয়ায় জাব পোকার আক্রমণ সবচেয়ে বেশি হয়।",
        },
    ),
    "lentil": (
        {
            "key": "stemphylium",
            "name_bn": "স্টেমফাইলিয়াম ব্লাইট",
            "name_en": "Stemphylium blight",
            "scientific": "Stemphylium botryosum",
            "kind": "disease",
            "kb_id": "lentil_disease_stemphylium",
            "stage": (40, 80),
            "temp_c": (18.0, 26.0),
            "humidity": 85.0,
            "prefers_dry": False,
            "wet_days": (2, 4),
            "why_bn": "উষ্ণ ও আর্দ্র রাতে স্টেমফাইলিয়াম ব্লাইট দ্রুত ছড়ায়।",
        },
        {
            "key": "pod_borer",
            "name_bn": "পড বোরার (ফল ছিদ্রকারী পোকা)",
            "name_en": "Pod borer",
            "scientific": "Helicoverpa armigera",
            "kind": "pest",
            "kb_id": "lentil_pest_podborer",
            "stage": (55, 95),
            "temp_c": (18.0, 30.0),
            "humidity": None,
            "prefers_dry": True,
            "wet_days": (3, 6),
            "why_bn": "শুঁটি ধরার সময় শুষ্ক উষ্ণ আবহাওয়ায় পড বোরারের আক্রমণ বাড়ে।",
        },
    ),
    "boro_rice": (
        {
            "key": "stem_borer",
            "name_bn": "কাণ্ড মাজরা পোকা",
            "name_en": "Rice stem borer",
            "scientific": "Scirpophaga incertulas",
            "kind": "pest",
            "kb_id": "boro_pest_stemborer",
            "stage": (20, 65),
            "temp_c": (22.0, 32.0),
            "humidity": None,
            "prefers_dry": False,
            "wet_days": (3, 6),
            "why_bn": "সর্বোচ্চ কুশি পর্যায়ে উষ্ণ আবহাওয়ায় মাজরা পোকার আক্রমণ বাড়ে।",
        },
        {
            "key": "bph",
            "name_bn": "বাদামি গাছ ফড়িং",
            "name_en": "Brown planthopper",
            "scientific": "Nilaparvata lugens",
            "kind": "pest",
            "kb_id": "boro_pest_bph",
            "stage": (45, 95),
            "temp_c": (25.0, 33.0),
            "humidity": 80.0,
            "prefers_dry": False,
            "wet_days": (3, 6),
            "why_bn": "গরম ও আর্দ্র আবহাওয়ায় ঘন গাছের গোড়ায় ফড়িং দ্রুত বংশবিস্তার করে।",
        },
    ),
    "aman_rice": (
        {
            "key": "yellow_stem_borer",
            "name_bn": "হলুদ কাণ্ড মাজরা পোকা",
            "name_en": "Yellow stem borer",
            "scientific": "Scirpophaga incertulas",
            "kind": "pest",
            "kb_id": "aman_pest_ysb",
            "stage": (18, 60),
            "temp_c": (24.0, 33.0),
            "humidity": None,
            "prefers_dry": False,
            "wet_days": (3, 6),
            "why_bn": "সর্বোচ্চ কুশি পর্যায়ে (২০–৩০ দিন) মাজরা পোকার আক্রমণ সবচেয়ে বেশি হয়।",
        },
        {
            "key": "blast",
            "name_bn": "ব্লাস্ট রোগ",
            "name_en": "Rice blast",
            "scientific": "Magnaporthe oryzae",
            "kind": "disease",
            "kb_id": "aman_disease_blast",
            "stage": (30, 85),
            "temp_c": (20.0, 28.0),
            "humidity": 88.0,
            "prefers_dry": False,
            "wet_days": (2, 4),
            "why_bn": "রাতে দীর্ঘ সময় পাতা ভেজা থাকলে ব্লাস্ট রোগ দ্রুত ছড়ায়।",
        },
        {
            "key": "sheath_blight",
            "name_bn": "খোলপোড়া রোগ (শীথ ব্লাইট)",
            "name_en": "Sheath blight",
            "scientific": "Rhizoctonia solani",
            "kind": "disease",
            "kb_id": "aman_disease_sheathblight",
            "stage": (40, 90),
            "temp_c": (25.0, 32.0),
            "humidity": 85.0,
            "prefers_dry": False,
            "wet_days": (2, 4),
            "why_bn": "গরম ও আর্দ্র অবস্থায় ঘন গাছের খোলে এই ছত্রাক দ্রুত বাড়ে।",
        },
    ),
}

_COST_NOTE_BN = (
    "চিকিৎসার আনুমানিক খরচ দেওয়া গেল না — কীটনাশক/ছত্রাকনাশকের কোনো "
    "নির্ভরযোগ্য, তারিখসহ দাম আমাদের উৎসে নেই। মাত্রা দেওয়া হলো; "
    "স্থানীয় ডিলারের কাছ থেকে দাম জেনে নিন।"
)
_COST_NOTE_EN = (
    "No citable Tk price exists for any pesticide/fungicide in this project's "
    "sources (data/prices.md has no pesticide rows; agristats.db fact_pesticides "
    "is national consumption tonnage). Dose is given; cost is withheld rather "
    "than estimated — CLAUDE.md rule 2."
)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _corpus_by_id() -> dict[str, dict]:
    try:
        raw = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = raw if isinstance(raw, list) else next(
        (v for v in raw.values() if isinstance(v, list)), []
    )
    return {row["id"]: row for row in rows if isinstance(row, dict) and "id" in row}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _matches(day: dict, rule: dict) -> bool:
    """Does one forecast day favour this organism?

    Humidity is used when the forecast carried it and the rule cares about it.
    When it did not, we fall back to "the day was wet" as a coarse proxy for
    leaf wetness — worse, but honest, and the caller is told via `degraded`.
    """
    tmax, tmin = day.get("tmax_c"), day.get("tmin_c")
    if tmax is None or tmin is None:
        return False
    mean_c = (float(tmax) + float(tmin)) / 2
    lo, hi = rule["temp_c"]
    if not (lo <= mean_c <= hi):
        return False

    precip = float(day.get("precip_mm") or 0.0)
    rh = day.get("humidity_pct")

    if rule["prefers_dry"]:
        return precip < 1.0

    if rule["humidity"] is None:
        return True  # temperature-only rule (borers): band match is the trigger
    if rh is not None:
        return float(rh) >= rule["humidity"]
    return precip >= 1.0  # proxy


def _level(matched: int, rule: dict) -> str:
    medium, high = rule["wet_days"]
    if matched >= high:
        return "high"
    if matched >= medium:
        return "medium"
    return "low"


def pest_risk(
    crop: str | None = None,
    farm_id: str | None = None,
    district: str | None = None,
    sowing_date: str | None = None,
) -> dict:
    """Live pest/disease risk for one crop at one farm's growth stage.

    Anything the caller omits is recovered from the saved plan and farm profile
    (Tier 1 persistent memory) rather than guessed. If the sowing date is still
    unknown after that, the tool refuses instead of assuming one — a wrong
    planting date silently shifts every stage window.
    """
    degraded: list[str] = []

    plan = get_plan(farm_id) if farm_id else None
    farm = get_farm(farm_id) if farm_id else None

    if not crop and isinstance(plan, dict):
        crop = plan.get("crop")
    if not sowing_date and isinstance(plan, dict):
        # The saved plan stores dated tasks, not the raw start date, so the
        # sowing task IS the sowing date — it is emitted at offset +0.
        sowing_date = next(
            (t.get("date") for t in plan.get("tasks", [])
             if isinstance(t, dict) and t.get("category") == "sowing"),
            None,
        )
    if not district and isinstance(farm, dict):
        district = farm.get("district")

    if crop not in _RULES:
        return {
            "error": "unsupported_crop",
            "crop": crop,
            "supported": sorted(_RULES),
            "degraded": "তথ্য যথেষ্ট নয়",
        }

    sown = _parse_date(sowing_date)
    if sown is None:
        return {
            "error": "sowing_date_required",
            "crop": crop,
            "message_bn": "রোপণের তারিখ ছাড়া বৃদ্ধির পর্যায় বের করা যায় না।",
            "degraded": "তথ্য যথেষ্ট নয়",
        }

    place = lookup_district(district) if district else None
    if place is None:
        return {
            "error": "district_required",
            "crop": crop,
            "message_bn": "জেলা ছাড়া আবহাওয়ার পূর্বাভাস আনা যায় না।",
            "degraded": "তথ্য যথেষ্ট নয়",
        }
    district_name, _division, lat, lon = place

    forecast = get_forecast(lat, lon, days=16)
    days = forecast.get("daily", []) or []
    if not days:
        degraded.append("আবহাওয়ার পূর্বাভাস পাওয়া যায়নি — ঝুঁকি নির্ণয় করা গেল না।")
    if days and all(d.get("humidity_pct") is None for d in days):
        degraded.append(
            "আর্দ্রতার তথ্য পাওয়া যায়নি; বৃষ্টির দিন দিয়ে আনুমানিক হিসাব করা হয়েছে।"
        )

    today = datetime.now(timezone.utc).date()
    das_today = (today - sown).days
    corpus = _corpus_by_id()

    risks: list[dict] = []
    for rule in _RULES[crop]:
        stage_lo, stage_hi = rule["stage"]
        passage = corpus.get(rule["kb_id"])

        # Only forecast days that fall inside this organism's susceptible window
        # count. A blight rule must not be scored on weather from before the
        # crop is even at risk.
        in_window = [
            day for index, day in enumerate(days)
            if stage_lo <= das_today + index <= stage_hi
        ]

        common = {
            "key": rule["key"],
            "kind": rule["kind"],
            "name_bn": rule["name_bn"],
            "name_en": rule["name_en"],
            "scientific_name": rule["scientific"],
            "stage_window_das": [stage_lo, stage_hi],
            "days_after_sowing_today": das_today,
            "treatment_cost_bdt": None,
            "treatment_cost_note_bn": _COST_NOTE_BN,
            "treatment_cost_note_en": _COST_NOTE_EN,
        }

        if das_today > stage_hi:
            risks.append({**common, "status": "past", "risk_level": None,
                          "why_bn": "এই পর্যায় পার হয়ে গেছে।"})
            continue

        if not in_window:
            # Susceptible window opens beyond the 16-day horizon. Saying
            # anything about its weather would be inventing a forecast.
            risks.append({
                **common,
                "status": "upcoming",
                "risk_level": None,
                "why_bn": (
                    f"ঝুঁকির সময় শুরু হবে রোপণের {stage_lo} দিন পর — "
                    "১৬ দিনের পূর্বাভাসের বাইরে, তাই এখনই ঝুঁকি বলা যাচ্ছে না।"
                ),
                "watch_from_date": (sown + timedelta(days=stage_lo)).isoformat(),
            })
            continue

        matched = [day for day in in_window if _matches(day, rule)]
        level = _level(len(matched), rule)
        risks.append({
            **common,
            "status": "active",
            "risk_level": level,
            "favourable_days": len(matched),
            "days_checked": len(in_window),
            "trigger_dates": [day["date"] for day in matched][:6],
            "why_bn": rule["why_bn"],
            "prevention_bn": (passage or {}).get("text"),
            "source_title": (passage or {}).get("source_title"),
            "locator": (passage or {}).get("locator"),
            "confidence": (passage or {}).get("confidence", "low"),
            "provenance": {
                "source_type": "computed",
                "source_id": f"pest_risk:{crop}:{rule['key']}",
                "source_title": (
                    "Stage window + Open-Meteo forecast; treatment from "
                    f"{(passage or {}).get('source_title', 'KB')}"
                ),
                "locator": (passage or {}).get("locator"),
                "formula": (
                    f"{len(matched)}/{len(in_window)} forecast days inside DAS "
                    f"{stage_lo}–{stage_hi} matched temp {rule['temp_c'][0]}–"
                    f"{rule['temp_c'][1]}°C"
                    + (f" and RH>={rule['humidity']}%" if rule["humidity"] else "")
                    + (" and dry" if rule["prefers_dry"] else "")
                    + f"; thresholds medium>={rule['wet_days'][0]}, high>={rule['wet_days'][1]}"
                ),
                "retrieved_at": _now_utc(),
                "confidence": (passage or {}).get("confidence", "low"),
            },
        })

    active = [r for r in risks if r["status"] == "active"]
    order = {"high": 3, "medium": 2, "low": 1}
    highest = max((r["risk_level"] for r in active), key=lambda lvl: order[lvl], default=None)

    return {
        "crop": crop,
        "district": district_name,
        "sowing_date": sown.isoformat(),
        "days_after_sowing": das_today,
        "assessed_on": today.isoformat(),
        "forecast_days": len(days),
        "forecast_source_type": forecast.get("source_type"),
        "forecast_cached": forecast.get("cached"),
        "highest_risk_level": highest,
        "risks": risks,
        "treatment_cost_available": False,
        "degraded": degraded,
        "retrieved_at": _now_utc(),
    }
