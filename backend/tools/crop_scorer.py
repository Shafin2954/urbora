"""crop_scorer.py — deterministic, unit-tested crop ranking (PRD §6).

Pure function `score_crops()`. The LLM never ranks crops itself — it narrates
this module's output (CLAUDE.md rule 1). Dependency status:

  * Finance engine (backend/finance/) -> BUILT. `crop_scorer_tool` now supplies
    the `finance` seam from `data/prices.md`, which switches on the Budget
    exclusion and the Profit component — but only once a crop actually has a
    cited price and cost row. While prices.md's farm-gate table is empty, this
    still reports unavailable, for a data reason rather than a code reason.
  * The cited AIS/BAMIS/BRRI facts in `backend/kb/crop_facts.py` drive the
    Season/Soil/Water exclusions and Agronomic fit + Climate fit components.
  * A component remains explicitly unavailable only when its live input (for
    example district climatology or a cited finance row) cannot be retrieved.

Pure core = no network, no DB writes. Reads crop.db/agribase_clean.db only via
cropdb.py's existing read-only functions. Climatology is injected by the caller,
never fetched inside the pure scoring core.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence, TypedDict

from ..schemas import (
    Confidence,
    CropCandidate,
    Provenance,
    RiskLevel,
    Season,
    ScoreComponent,
    SoilType,
    SourceType,
    WaterNeed,
    WaterSource,
)
from .cropdb import (
    CANON_TO_KEY,
    district_yields,
    holt_projection,
    resolve_crop,
    yield_track_record,
)
from .districts import lookup_district
from .districts import DISTRICTS
from backend.units import to_hectares

DEFAULT_CANDIDATES: tuple[str, ...] = ("boro_rice", "aman_rice", "potato", "mustard", "lentil")

# Water-access ranking, higher = more reliable irrigation access. A tubewell
# (farmer's own lift/shallow pump, on-demand) is strictly better access than a
# shared canal (scheduled, contested, seasonal) — NOT worse. PRD.md §6's prose
# table literally reads "rainfed < tubewell < canal/irrigated", which is
# backwards from real BD agronomy and, left uncorrected here, silently
# excluded boro rice — the single most important Rabi crop, overwhelmingly
# shallow-tubewell irrigated — for every tubewell-only farm (boro's
# water_min_rank=2 in kb/crop_facts.py was unreachable via tubewell under the
# old ranks). Fixed 2026-07-25; PRD.md wording still needs a matching
# correction by whoever owns it (out of this instance's directories).
WATER_RANK: dict[str, int] = {"rainfed": 0, "canal": 1, "tubewell": 2, "irrigated": 2}


@dataclass(frozen=True)
class CropFacts:
    """A cited, deterministic agronomy record for one supported crop."""

    crop: str
    seasons: frozenset[str]          # Season literals this crop is sown in
    soil_primary: frozenset[str]     # SoilType literals: best fit (25 pts)
    soil_secondary: frozenset[str]   # SoilType literals: workable fit (15 pts)
    soil_marginal: frozenset[str]    # SoilType literals: poor but possible (8 pts)
    water_min_rank: int              # minimum WATER_RANK the farm must have
    water_need: WaterNeed
    temp_opt_c: tuple[float, float]  # (lo, hi) optimal mean tmax over growing months
    rain_opt_mm: tuple[float, float] # (lo, hi) optimal total rain over growing months
    growing_months: frozenset[int]   # 1-12
    source_id: str = "crop_facts"
    source_title: str = "AgriSense crop agronomy facts"
    locator: str | None = None


class CropFinance(TypedDict):
    """The finance seam. B fills this once backend/finance/ exists."""

    min_cost_per_ha: float
    net_profit_bdt_per_ha: float
    source_id: str
    source_title: str
    formula: str
    # "complete" (BBS aggregate expenditure) vs "partial_fertilizer_only"
    # (fertiliser-doses-only minimum bound). Read via .get() with a
    # "complete" default everywhere below, since synthetic finance dicts in
    # tests and any pre-2026-07-25 caller never populate this key.
    cost_basis: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _prov(
    value: int | float | str,
    *,
    source_type: SourceType,
    source_id: str,
    source_title: str,
    retrieved_at: str,
    confidence: Confidence = "medium",
    formula: str | None = None,
    locator: str | None = None,
    unit: str | None = None,
) -> Provenance:
    return Provenance(
        value=value,
        unit=unit,
        source_type=source_type,
        source_id=source_id,
        source_title=source_title,
        locator=locator,
        retrieved_at=retrieved_at,
        formula=formula,
        confidence=confidence,
    )


def _provenance_from_raw(raw: dict, value: int | float | str) -> Provenance | None:
    """Convert one of cropdb.py's result dicts (already carrying source_type /
    source_id / source_title / confidence / retrieved_at) into a Provenance for
    a candidate's extra-sources list. None if the raw result errored."""
    if raw.get("error"):
        return None
    return Provenance(
        value=value,
        source_type=raw.get("source_type", "dataset"),
        source_id=raw.get("source_id", "unknown"),
        source_title=raw.get("source_title", "unknown"),
        locator=raw.get("locator"),
        retrieved_at=raw.get("retrieved_at") or raw.get("fitted_at") or _now(),
        formula=raw.get("formula"),
        confidence=raw.get("confidence", "medium"),
    )


def _unavailable_component(name: str, max_points: float, reason: str, now: str) -> ScoreComponent:
    return ScoreComponent(
        name=name,
        points=0.0,
        max=max_points,
        provenance=_prov(
            "unavailable",
            source_type="computed",
            source_id="crop_scorer",
            source_title="AgriSense crop scorer",
            confidence="low",
            formula=reason,
            retrieved_at=now,
        ),
    )


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _district_cv(observations: list[dict]) -> float | None:
    """CV of THIS district's own yearly yield history — Stability's basis
    (over-time trust in a track record). Distinct from District track record's
    cross-district percentile. None if fewer than 2 usable points."""
    vals = [o["yield_kg_ha"] for o in observations if o.get("yield_kg_ha") is not None]
    if len(vals) < 2:
        return None
    mean = statistics.mean(vals)
    if mean == 0:
        return None
    return statistics.pstdev(vals) / mean


def _risk_level(cv: float | None, known_cvs: list[float]) -> RiskLevel:
    """Risk from Stability's CV: relative terciles across survivors with a
    computable CV (needs >=3), else fixed thresholds."""
    if cv is None:
        return "high"  # unknown stability -> conservative "high risk"
    known = sorted(known_cvs)
    if len(known) >= 3:
        frac = sum(1 for v in known if v <= cv) / len(known)
        if frac <= 1 / 3:
            return "low"
        if frac <= 2 / 3:
            return "medium"
        return "high"
    if cv < 0.10:
        return "low"
    if cv <= 0.20:
        return "medium"
    return "high"


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 components
# ─────────────────────────────────────────────────────────────────────────────
def _agronomic_fit(soil_type: str, facts: CropFacts | None, now: str) -> ScoreComponent:
    if facts is None:
        return _unavailable_component(
            "Agronomic fit", 25.0, "KB soil-compatibility data not yet curated", now
        )
    if soil_type in facts.soil_primary:
        points = 25.0
    elif soil_type in facts.soil_secondary:
        points = 15.0
    elif soil_type in facts.soil_marginal:
        points = 8.0
    else:
        points = 0.0
    return ScoreComponent(
        name="Agronomic fit",
        points=points,
        max=25.0,
        provenance=_prov(
            points,
            source_type="static_table",
            source_id=facts.source_id,
            source_title=facts.source_title,
            locator=facts.locator,
            formula=f"soil '{soil_type}' vs {facts.crop}: primary=25/secondary=15/marginal=8",
            retrieved_at=now,
        ),
    )


def _profit(
    crop: str,
    area_ha: float | None,
    finance: dict[str, CropFinance] | None,
    profit_range: tuple[float, float] | None,
    now: str,
) -> tuple[ScoreComponent, float]:
    if finance is None or crop not in finance:
        return _unavailable_component("Profit", 25.0, "finance engine not yet built", now), 0.0
    fin = finance[crop]
    raw = fin["net_profit_bdt_per_ha"]
    est_profit = raw * area_ha if area_ha is not None else raw
    cost_basis = fin.get("cost_basis", "complete")
    if cost_basis != "complete":
        # This crop's cost line is a fertiliser-only minimum bound (see
        # prices.md §2), not a full cost of cultivation, so its ROI/profit is
        # structurally incomparable to a crop costed against BBS's complete
        # aggregate expenditure — the crop with the LEAST complete cost data
        # would otherwise win the min-max normalization every time. Neutral
        # zero points, never scored from this basis; est_profit_bdt is still
        # reported (it is real data, not invented) but the tool-level
        # `degraded` list must say plainly that it is not comparable.
        component = ScoreComponent(
            name="Profit",
            points=0.0,
            max=25.0,
            provenance=_prov(
                raw,
                unit="BDT/ha",
                source_type="computed",
                source_id=fin["source_id"],
                source_title=fin["source_title"],
                formula=(
                    fin["formula"] + f"; cost_basis={cost_basis} (minimum bound, "
                    "not a complete cost of cultivation) — excluded from Profit "
                    "scoring and from the min-max range of crops with complete "
                    "cost data"
                ),
                confidence="low",
                retrieved_at=now,
            ),
        )
        return component, est_profit
    if profit_range is None:
        points = 25.0
    else:
        lo, hi = profit_range
        points = 25.0 if hi == lo else 25.0 * (raw - lo) / (hi - lo)
    points = round(_clamp(points, 0.0, 25.0), 2)
    component = ScoreComponent(
        name="Profit",
        points=points,
        max=25.0,
        provenance=_prov(
            raw,
            unit="BDT/ha",
            source_type="computed",
            source_id=fin["source_id"],
            source_title=fin["source_title"],
            formula=fin["formula"] + "; min-max normalized within candidate set",
            retrieved_at=now,
        ),
    )
    return component, est_profit


def _climate_fit(facts: CropFacts | None, climatology: dict | None, now: str) -> ScoreComponent:
    if facts is None:
        return _unavailable_component(
            "Climate fit", 20.0, "crop climate-optimal bands not yet curated", now
        )
    if not climatology or not climatology.get("normals"):
        return _unavailable_component(
            "Climate fit", 20.0, "climatology unavailable for this location", now
        )
    normals = [n for n in climatology["normals"] if n.get("month") in facts.growing_months]
    if not normals:
        return _unavailable_component(
            "Climate fit", 20.0, "no climatology data for this crop's growing months", now
        )
    tmax_vals = [n["tmax_c_avg"] for n in normals if n.get("tmax_c_avg") is not None]
    rain_vals = [n["precip_mm_avg"] for n in normals if n.get("precip_mm_avg") is not None]
    mean_tmax = statistics.mean(tmax_vals) if tmax_vals else None
    total_rain = sum(rain_vals) if rain_vals else None

    def _penalty(val: float | None, lo: float, hi: float, weight: float) -> float:
        if val is None:
            return weight
        if lo <= val <= hi:
            return 0.0
        band = hi - lo
        dist = (lo - val) if val < lo else (val - hi)
        return weight if band <= 0 else weight * min(1.0, dist / band)

    temp_lo, temp_hi = facts.temp_opt_c
    rain_lo, rain_hi = facts.rain_opt_mm
    temp_pen = _penalty(mean_tmax, temp_lo, temp_hi, 10.0)
    rain_pen = _penalty(total_rain, rain_lo, rain_hi, 10.0)
    points = round(_clamp(20.0 - temp_pen - rain_pen, 0.0, 20.0), 2)
    return ScoreComponent(
        name="Climate fit",
        points=points,
        max=20.0,
        provenance=_prov(
            points,
            source_type="computed",
            source_id=facts.source_id,
            source_title=facts.source_title,
            locator=facts.locator,
            formula=(
                f"mean_tmax={mean_tmax}, total_rain={total_rain} vs optimal "
                f"temp={facts.temp_opt_c}, rain={facts.rain_opt_mm} over growing months"
            ),
            retrieved_at=now,
        ),
    )


def _district_track_record(crop: str, district: str, now: str) -> tuple[ScoreComponent, dict, dict]:
    tr = yield_track_record(crop, district)
    hp = holt_projection(crop, district)
    if tr.get("error"):
        return _unavailable_component(
            "District track record", 20.0, f"track record unavailable: {tr['error']}", now
        ), tr, hp
    pct = tr["percentile_vs_districts"]
    trend = hp.get("trend", "flat")
    trend_adj = 2.0 if trend == "up" else (-2.0 if trend == "down" else 0.0)
    points = round(_clamp(pct / 100.0 * 18.0 + trend_adj, 0.0, 20.0), 2)
    component = ScoreComponent(
        name="District track record",
        points=points,
        max=20.0,
        provenance=_prov(
            points,
            source_type="computed",
            source_id="crop_scorer",
            source_title="AgriSense crop scorer",
            formula=(
                f"percentile {pct} -> 0-18 scale + Holt trend '{trend}' "
                f"adjustment {trend_adj:+.0f}"
            ),
            retrieved_at=now,
        ),
    )
    return component, tr, hp


def _stability(crop: str, district: str, now: str) -> tuple[ScoreComponent, dict, float | None]:
    dy = district_yields(crop, district)
    cv = _district_cv(dy.get("observations", []))
    if cv is None:
        return _unavailable_component(
            "Stability", 10.0, "fewer than 2 years of yield history — cannot compute CV", now
        ), dy, None
    points = round(_clamp(10.0 * (1.0 - cv), 0.0, 10.0), 2)
    component = ScoreComponent(
        name="Stability",
        points=points,
        max=10.0,
        provenance=_prov(
            points,
            source_type="dataset",
            source_id="agribase_clean",
            source_title="Validated derivative of supplied district yield dataset",
            formula=f"10*(1-CV) of {len(dy.get('observations', []))} yearly yields, CV={cv:.3f}",
            retrieved_at=now,
        ),
    )
    return component, dy, cv


# ─────────────────────────────────────────────────────────────────────────────
# Public entrypoint (pure)
# ─────────────────────────────────────────────────────────────────────────────
def score_crops(
    *,
    district: str,
    soil_type: SoilType,
    water_source: WaterSource,
    season: Season,
    candidates: Sequence[str] = DEFAULT_CANDIDATES,
    area_ha: float | None = None,
    budget_bdt: float | None = None,
    finance: dict[str, CropFinance] | None = None,
    climatology_by_crop: dict[str, dict] | None = None,
    crop_facts: dict[str, CropFacts] | None = None,
    now: str | None = None,
) -> list[CropCandidate]:
    """Deterministic crop ranking (PRD §6). Pure: no network, no DB writes.

    Reads crop.db/agribase_clean.db only via cropdb.py's read-only functions.
    Season/Soil/Water exclusions and Agronomic fit/Climate fit only activate when
    `crop_facts` is supplied for a crop (KB seam, unpopulated today). Budget
    exclusion/Profit component only activate when `finance` + `area_ha` +
    `budget_bdt` are supplied (finance seam, unpopulated today). Missing seams
    degrade honestly (component reports "unavailable"), never fabricate a number.
    """
    ts = now or _now()
    hit = lookup_district(district)
    district_name = hit[0] if hit else district

    survivors: list[str] = []
    excluded: dict[str, tuple[str, list[Provenance]]] = {}

    for crop in candidates:
        if resolve_crop(crop) is None:
            excluded[crop] = (f"no yield data for '{crop}' (not a supported crop)", [])
            continue

        facts = crop_facts.get(crop) if crop_facts else None
        if facts is not None:
            if season not in facts.seasons:
                reason = (
                    f"Not sown in {season}; {crop} is a "
                    f"{'/'.join(sorted(facts.seasons))} crop."
                )
                notes = [_prov(season, source_type="static_table", source_id=facts.source_id,
                               source_title=facts.source_title, locator=facts.locator,
                               formula="season exclusion", retrieved_at=ts)]
                excluded[crop] = (reason, notes)
                continue
            allowed_soil = facts.soil_primary | facts.soil_secondary | facts.soil_marginal
            if soil_type not in allowed_soil:
                reason = (
                    f"{soil_type} soil is unsuitable for {crop} "
                    f"(suited to: {sorted(allowed_soil)})."
                )
                notes = [_prov(soil_type, source_type="static_table", source_id=facts.source_id,
                               source_title=facts.source_title, locator=facts.locator,
                               formula="soil exclusion", retrieved_at=ts)]
                excluded[crop] = (reason, notes)
                continue
            if WATER_RANK.get(water_source, 0) < facts.water_min_rank:
                reason = (
                    f"{crop} needs at least water rank {facts.water_min_rank}; "
                    f"farm has '{water_source}' (rank {WATER_RANK.get(water_source, 0)})."
                )
                notes = [_prov(water_source, source_type="static_table", source_id=facts.source_id,
                               source_title=facts.source_title, locator=facts.locator,
                               formula="water exclusion", retrieved_at=ts)]
                excluded[crop] = (reason, notes)
                continue

        if finance and area_ha is not None and budget_bdt is not None and crop in finance:
            total_cost = finance[crop]["min_cost_per_ha"] * area_ha
            if total_cost > budget_bdt:
                reason = (
                    f"Minimum cost {total_cost:.0f} BDT "
                    f"({finance[crop]['min_cost_per_ha']:.0f}/ha x {area_ha} ha) "
                    f"exceeds budget {budget_bdt:.0f} BDT."
                )
                notes = [_prov(total_cost, unit="BDT", source_type="computed",
                               source_id=finance[crop]["source_id"],
                               source_title=finance[crop]["source_title"],
                               formula="min_cost_per_ha * area_ha vs budget", retrieved_at=ts)]
                excluded[crop] = (reason, notes)
                continue
        # Otherwise the budget check is skipped because a needed finance input is absent.

        survivors.append(crop)

    # Stage 2: compute per-survivor raw components (profit needs a second pass
    # for min-max normalization across the set).
    scored: dict[str, dict] = {}
    for crop in survivors:
        facts = crop_facts.get(crop) if crop_facts else None
        climatology = climatology_by_crop.get(crop) if climatology_by_crop else None
        track_record, tr_raw, hp_raw = _district_track_record(crop, district_name, ts)
        stability, dy_raw, cv = _stability(crop, district_name, ts)
        scored[crop] = {
            "agronomic": _agronomic_fit(soil_type, facts, ts),
            "climate": _climate_fit(facts, climatology, ts),
            "track_record": track_record,
            "tr_raw": tr_raw,
            "hp_raw": hp_raw,
            "stability": stability,
            "dy_raw": dy_raw,
            "cv": cv,
            "facts": facts,
        }

    # Only crops with a complete cost basis participate in the Profit
    # min-max range — a partial (fertiliser-only) basis is not a fair
    # comparison point (see `_profit`'s docstring-length comment above).
    profit_raws = [
        finance[c]["net_profit_bdt_per_ha"]
        for c in survivors
        if finance and c in finance and finance[c].get("cost_basis", "complete") == "complete"
    ]
    profit_range = (min(profit_raws), max(profit_raws)) if profit_raws else None
    known_cvs = [d["cv"] for d in scored.values() if d["cv"] is not None]

    results: list[CropCandidate] = []
    for crop in survivors:
        d = scored[crop]
        profit_component, est_profit = _profit(crop, area_ha, finance, profit_range, ts)
        components = [
            d["agronomic"], profit_component, d["climate"], d["track_record"], d["stability"],
        ]
        composite = round(sum(c.points for c in components), 2)
        water_need: WaterNeed = d["facts"].water_need if d["facts"] is not None else "medium"

        extra_provenance: list[Provenance] = []
        p = _provenance_from_raw(d["tr_raw"], d["tr_raw"].get("percentile_vs_districts", "n/a"))
        if p:
            extra_provenance.append(p)
        p = _provenance_from_raw(d["hp_raw"], d["hp_raw"].get("base_yield_kg_ha", "n/a"))
        if p:
            extra_provenance.append(p)
        p = _provenance_from_raw(d["dy_raw"], len(d["dy_raw"].get("observations", [])))
        if p:
            extra_provenance.append(p)

        results.append(
            CropCandidate(
                crop=crop,
                composite_score=composite,
                components=components,
                excluded=False,
                exclusion_reason=None,
                water_need=water_need,
                risk_level=_risk_level(d["cv"], known_cvs),
                est_profit_bdt=round(est_profit, 2),
                provenance=extra_provenance,
            )
        )

    for crop, (reason, notes) in excluded.items():
        cv = None
        if resolve_crop(crop) is not None:
            dy = district_yields(crop, district_name)
            cv = _district_cv(dy.get("observations", []))
        water_need_excl: WaterNeed = (
            crop_facts[crop].water_need if crop_facts and crop in crop_facts else "medium"
        )
        results.append(
            CropCandidate(
                crop=crop,
                composite_score=0.0,
                components=[],
                excluded=True,
                exclusion_reason=reason,
                water_need=water_need_excl,
                risk_level=_risk_level(cv, known_cvs),
                est_profit_bdt=0.0,
                provenance=notes,
            )
        )

    results.sort(key=lambda c: (c.excluded, -c.composite_score))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Impure agent-facing wrapper — this is what tools_spec.py registers.
# ─────────────────────────────────────────────────────────────────────────────
def crop_scorer_tool(
    *,
    district: str,
    soil_type: str,
    water_source: str,
    season: str,
    candidates: list[str] | None = None,
    area: float | None = None,
    area_unit: str = "hectare",
    budget_bdt: float | None = None,
) -> dict:
    """Agent tool entrypoint.

    `area`/`area_unit`, not `area_ha`: the caller (the LLM) passes the farmer's
    area in whatever unit they stated it in, and this function converts once,
    server-side, via units.to_hectares — mirroring finance_projection's pattern
    exactly. CLAUDE.md rule 1 forbids the model from ever doing unit arithmetic
    itself; a bare `area_ha` param silently required exactly that (bug found
    2026-07-24: 3 bigha was passed straight through as if it were 3 hectares,
    a 7.47x profit overstatement — logged in LOG3.md).

    `finance` is supplied from `data/prices.md` when — and only when — every
    candidate has a cited price and cost (see `PriceCatalog.scorer_finance`).
    That switches on the Profit component and the Budget exclusion. Partial
    coverage supplies nothing at all, because PRD §6 normalizes Profit min-max
    *within the candidate set*: scoring three crops and not the other two would
    rank the uncited ones down for lacking a citation rather than for being
    worse crops.

    `crop_facts=None` still: Agronomic/Climate fit and the season/soil/water
    screening wait on the curated KB. Climatology fetch is skipped with them,
    since Climate fit needs both — fetching it now would spend an API call for
    nothing.
    """
    # Delayed import avoids a type-definition cycle: the KB data is expressed
    # as CropFacts instances defined in this module.
    from backend.kb.crop_facts import CROP_FACTS

    crops = candidates or DEFAULT_CANDIDATES
    finance, finance_gap = _finance_for(crops, district)
    area_ha = to_hectares(area, area_unit) if area is not None else None
    canonical = lookup_district(district)
    climate: dict[str, dict] | None = None
    if canonical and canonical[0] in DISTRICTS:
        from .weather import get_climatology

        _division, lat, lon = DISTRICTS[canonical[0]]
        climate_result = get_climatology(lat, lon)
        if not climate_result.get("error") and climate_result.get("normals"):
            climate = {crop: climate_result for crop in crops}

    try:
        results = score_crops(
            district=district,
            soil_type=soil_type,  # type: ignore[arg-type]
            water_source=water_source,  # type: ignore[arg-type]
            season=season,  # type: ignore[arg-type]
            candidates=crops,
            area_ha=area_ha,
            budget_bdt=budget_bdt,
            finance=finance,
            climatology_by_crop=climate,
            crop_facts=CROP_FACTS,
        )
    except Exception as e:  # noqa: BLE001 — never crash the agent turn
        return {"error": f"crop_scorer failed: {e}"}

    degraded = []
    if climate is None:
        degraded.append(
            "Climate fit component: unavailable because district climatology could not be retrieved; "
            "season/soil/water screening and Agronomic fit use cited crop facts."
        )
    if finance is None:
        degraded.append(f"Profit component and Budget screening: unavailable — {finance_gap}")
    elif finance:
        partial_basis_crops = sorted(
            c for c in crops if c in finance and finance[c].get("cost_basis", "complete") != "complete"
        )
        if partial_basis_crops:
            degraded.append(
                f"{'/'.join(partial_basis_crops)} cost data is fertiliser-only (minimum bound); "
                "profit not comparable across crops"
            )
        # Sanity backstop, not a hard rule: a >150% ROI is not impossible for
        # BD field crops but is unusual enough to be worth a flag rather than
        # a silent, confident-looking number — especially useful if a future
        # price/cost row is mistyped the way potato's 2024-25 harvest price
        # was (2026-07-25 fix, see prices.md).
        high_roi_crops = sorted(
            c for c in crops
            if c in finance and finance[c].get("min_cost_per_ha", 0) > 0
            and (finance[c]["net_profit_bdt_per_ha"] / finance[c]["min_cost_per_ha"]) > 1.5
        )
        if high_roi_crops:
            degraded.append(
                f"{'/'.join(high_roi_crops)}: computed ROI exceeds 150% — plausible but unusual; "
                "treat as a data sanity flag, not a guarantee"
            )

    return {
        "candidates": [c.model_dump() for c in results],
        "degraded": degraded,
    }


def _finance_for(crops: list[str], district: str) -> tuple[dict | None, str | None]:
    """Assemble the finance seam for this district's candidate set.

    Revenue per hectare needs a yield, and the yield is district-specific, so
    this pairs each crop's damped-Holt base with its cited price. A crop whose
    projection is missing is reported as ungettable rather than defaulted.
    """
    try:
        from backend.finance import load_catalog

        yields: dict[str, float] = {}
        for crop in crops:
            projection = holt_projection(crop, district)
            if "error" not in projection:
                yields[crop] = projection["base_yield_kg_ha"]
        return load_catalog().scorer_finance(crops, yields)
    except Exception as e:  # noqa: BLE001 — a price-file problem must not kill ranking
        return None, f"finance inputs could not be read ({e})"


if __name__ == "__main__":
    import json
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass
    out = crop_scorer_tool(district="Rajshahi", soil_type="clay_loam",
                           water_source="tubewell", season="rabi")
    print(json.dumps(out, indent=2, ensure_ascii=False))
