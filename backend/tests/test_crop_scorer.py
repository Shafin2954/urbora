"""Tests for backend/tools/crop_scorer.py — the deterministic PRD §6 ranker.

Today's real config is crop_facts=None, finance=None, climatology_by_crop=None
(no curated KB, no finance engine yet — human decision, LOG1.md 2026-07-24).
Most tests exercise that real degraded mode against Rajshahi (real crop.db
data). A few construct synthetic CropFacts/CropFinance/climatology (test-only,
never shipped) to prove the future KB/finance-backed code path already works.
"""

from __future__ import annotations

import sys
import types

import pytest

from backend.tools import crop_scorer as cs
from backend.tools.crop_scorer import (
    CropFacts,
    _district_cv,
    _risk_level,
    score_crops,
)

RAJSHAHI = "Rajshahi"
ALL_5 = ("boro_rice", "aman_rice", "potato", "mustard", "lentil")


def _by_crop(results):
    return {c.crop: c for c in results}


# ── 1. unsupported crops ─────────────────────────────────────────────────────
@pytest.mark.parametrize("crop", ["wheat", "maize", "not_a_crop"])
def test_unsupported_crop_excluded_honestly(crop):
    results = score_crops(
        district=RAJSHAHI, soil_type="clay_loam", water_source="tubewell", season="rabi",
        candidates=[crop],
    )
    assert len(results) == 1
    c = results[0]
    assert c.excluded is True
    assert "no yield data" in c.exclusion_reason
    assert c.components == []
    assert c.composite_score == 0.0


# ── 2. today's real degraded mode ────────────────────────────────────────────
def test_degraded_mode_marks_kb_and_finance_components_unavailable():
    results = score_crops(
        district=RAJSHAHI, soil_type="clay_loam", water_source="tubewell", season="rabi",
        candidates=ALL_5,
    )
    by_crop = _by_crop(results)
    assert set(by_crop) == set(ALL_5)
    for crop, c in by_crop.items():
        assert c.excluded is False, f"{crop} unexpectedly excluded: {c.exclusion_reason}"
        names = {comp.name: comp for comp in c.components}
        assert names["Agronomic fit"].points == 0.0
        assert names["Agronomic fit"].provenance.confidence == "low"
        assert names["Profit"].points == 0.0
        assert names["Climate fit"].points == 0.0
        assert c.est_profit_bdt == 0.0
        # District track record + Stability DO work today for crops with history
        assert names["Stability"].points > 0.0
        assert names["District track record"].max == 20.0


def test_degraded_mode_water_need_defaults_neutral_when_facts_absent():
    results = score_crops(
        district=RAJSHAHI, soil_type="loam", water_source="rainfed", season="rabi",
        candidates=["boro_rice"],
    )
    assert results[0].water_need == "medium"


# ── 3. composite == sum of components ────────────────────────────────────────
def test_composite_equals_sum_of_component_points_degraded():
    results = score_crops(
        district=RAJSHAHI, soil_type="clay_loam", water_source="tubewell", season="rabi",
        candidates=ALL_5,
    )
    for c in results:
        if not c.excluded:
            assert c.composite_score == round(sum(comp.points for comp in c.components), 2)


# ── 4. synthetic future path: exclusions ─────────────────────────────────────
def test_season_exclusion_with_synthetic_facts():
    facts = {
        "aman_rice": CropFacts(
            crop="aman_rice", seasons=frozenset({"kharif2"}),
            soil_primary=frozenset({"clay"}), soil_secondary=frozenset(),
            soil_marginal=frozenset(), water_min_rank=0, water_need="medium",
            temp_opt_c=(24.0, 34.0), rain_opt_mm=(600.0, 1400.0),
            growing_months=frozenset({7, 8, 9}),
        ),
    }
    results = score_crops(
        district=RAJSHAHI, soil_type="clay", water_source="rainfed", season="rabi",
        candidates=["aman_rice"], crop_facts=facts,
    )
    c = results[0]
    assert c.excluded is True
    assert "kharif2" in c.exclusion_reason and "rabi" in c.exclusion_reason


def test_soil_exclusion_with_synthetic_facts():
    facts = {
        "boro_rice": CropFacts(
            crop="boro_rice", seasons=frozenset({"rabi"}),
            soil_primary=frozenset({"sandy"}), soil_secondary=frozenset(),
            soil_marginal=frozenset(), water_min_rank=0, water_need="high",
            temp_opt_c=(20.0, 35.0), rain_opt_mm=(0.0, 500.0),
            growing_months=frozenset({1, 2, 3}),
        ),
    }
    results = score_crops(
        district=RAJSHAHI, soil_type="clay", water_source="tubewell", season="rabi",
        candidates=["boro_rice"], crop_facts=facts,
    )
    c = results[0]
    assert c.excluded is True
    assert "soil" in c.exclusion_reason.lower()


def test_water_exclusion_with_synthetic_facts():
    facts = {
        "boro_rice": CropFacts(
            crop="boro_rice", seasons=frozenset({"rabi"}),
            soil_primary=frozenset({"clay_loam"}), soil_secondary=frozenset(),
            soil_marginal=frozenset(), water_min_rank=2, water_need="high",
            temp_opt_c=(20.0, 35.0), rain_opt_mm=(0.0, 500.0),
            growing_months=frozenset({1, 2, 3}),
        ),
    }
    results = score_crops(
        district=RAJSHAHI, soil_type="clay_loam", water_source="rainfed", season="rabi",
        candidates=["boro_rice"], crop_facts=facts,
    )
    c = results[0]
    assert c.excluded is True
    assert "water" in c.exclusion_reason.lower()


def test_budget_exclusion_applied_when_finance_and_area_and_budget_present():
    finance = {
        "boro_rice": {
            "min_cost_per_ha": 200_000.0, "net_profit_bdt_per_ha": 10_000.0,
            "source_id": "test", "source_title": "test finance", "formula": "test",
        },
    }
    results = score_crops(
        district=RAJSHAHI, soil_type="clay_loam", water_source="tubewell", season="rabi",
        candidates=["boro_rice"], area_ha=1.0, budget_bdt=50_000.0, finance=finance,
    )
    c = results[0]
    assert c.excluded is True
    assert "cost" in c.exclusion_reason.lower()
    assert "200000" in c.exclusion_reason


def test_budget_exclusion_skipped_when_finance_absent():
    # Tiny budget would exclude everything IF a placeholder cost were fabricated —
    # it must not be. Crop survives; Profit reports unavailable instead.
    results = score_crops(
        district=RAJSHAHI, soil_type="clay_loam", water_source="tubewell", season="rabi",
        candidates=["boro_rice"], area_ha=1.0, budget_bdt=1.0, finance=None,
    )
    c = results[0]
    assert c.excluded is False
    profit = next(comp for comp in c.components if comp.name == "Profit")
    assert profit.points == 0.0 and profit.provenance.confidence == "low"


# ── Agronomic fit bucket scoring ─────────────────────────────────────────────
@pytest.mark.parametrize(
    "soil_type,bucket,expected_points",
    [("loam", "soil_primary", 25.0), ("silt", "soil_secondary", 15.0), ("sandy", "soil_marginal", 8.0)],
)
def test_agronomic_fit_buckets(soil_type, bucket, expected_points):
    kwargs = {"soil_primary": frozenset(), "soil_secondary": frozenset(), "soil_marginal": frozenset()}
    kwargs[bucket] = frozenset({soil_type})
    facts = {
        "boro_rice": CropFacts(
            crop="boro_rice", seasons=frozenset({"rabi"}), water_min_rank=0,
            water_need="high", temp_opt_c=(20.0, 35.0), rain_opt_mm=(0.0, 500.0),
            growing_months=frozenset({1, 2, 3}), **kwargs,
        ),
    }
    results = score_crops(
        district=RAJSHAHI, soil_type=soil_type, water_source="tubewell", season="rabi",
        candidates=["boro_rice"], crop_facts=facts,
    )
    agro = next(comp for comp in results[0].components if comp.name == "Agronomic fit")
    assert agro.points == expected_points


# ── Profit normalization ──────────────────────────────────────────────────────
def test_profit_min_max_normalization_across_survivors():
    finance = {
        "boro_rice": {"min_cost_per_ha": 1000.0, "net_profit_bdt_per_ha": 50_000.0,
                      "source_id": "t", "source_title": "t", "formula": "t"},
        "aman_rice": {"min_cost_per_ha": 1000.0, "net_profit_bdt_per_ha": 10_000.0,
                      "source_id": "t", "source_title": "t", "formula": "t"},
    }
    results = score_crops(
        district=RAJSHAHI, soil_type="clay_loam", water_source="tubewell", season="rabi",
        candidates=["boro_rice", "aman_rice"], area_ha=2.0, finance=finance,
    )
    by_crop = _by_crop(results)
    hi = next(c for c in by_crop["boro_rice"].components if c.name == "Profit")
    lo = next(c for c in by_crop["aman_rice"].components if c.name == "Profit")
    assert hi.points == 25.0
    assert lo.points == 0.0
    assert by_crop["boro_rice"].est_profit_bdt == 100_000.0  # 50000 * 2 ha


def test_profit_single_survivor_gets_full_points():
    finance = {"boro_rice": {"min_cost_per_ha": 1000.0, "net_profit_bdt_per_ha": 30_000.0,
                             "source_id": "t", "source_title": "t", "formula": "t"}}
    results = score_crops(
        district=RAJSHAHI, soil_type="clay_loam", water_source="tubewell", season="rabi",
        candidates=["boro_rice"], finance=finance,
    )
    profit = next(c for c in results[0].components if c.name == "Profit")
    assert profit.points == 25.0


# ── Climate fit ───────────────────────────────────────────────────────────────
def test_climate_fit_within_optimal_band_scores_full():
    facts = {
        "boro_rice": CropFacts(
            crop="boro_rice", seasons=frozenset({"rabi"}), soil_primary=frozenset({"clay_loam"}),
            soil_secondary=frozenset(), soil_marginal=frozenset(), water_min_rank=0,
            water_need="high", temp_opt_c=(20.0, 35.0), rain_opt_mm=(0.0, 50.0),
            growing_months=frozenset({1, 2}),
        ),
    }
    climatology = {"boro_rice": {"normals": [
        {"month": 1, "tmax_c_avg": 25.0, "precip_mm_avg": 5.0},
        {"month": 2, "tmax_c_avg": 27.0, "precip_mm_avg": 5.0},
    ]}}
    results = score_crops(
        district=RAJSHAHI, soil_type="clay_loam", water_source="tubewell", season="rabi",
        candidates=["boro_rice"], crop_facts=facts, climatology_by_crop=climatology,
    )
    climate = next(c for c in results[0].components if c.name == "Climate fit")
    assert climate.points == 20.0


def test_climate_fit_far_outside_optimal_band_penalized_not_negative():
    facts = {
        "boro_rice": CropFacts(
            crop="boro_rice", seasons=frozenset({"rabi"}), soil_primary=frozenset({"clay_loam"}),
            soil_secondary=frozenset(), soil_marginal=frozenset(), water_min_rank=0,
            water_need="high", temp_opt_c=(20.0, 25.0), rain_opt_mm=(0.0, 10.0),
            growing_months=frozenset({7}),
        ),
    }
    climatology = {"boro_rice": {"normals": [
        {"month": 7, "tmax_c_avg": 45.0, "precip_mm_avg": 500.0},
    ]}}
    results = score_crops(
        district=RAJSHAHI, soil_type="clay_loam", water_source="tubewell", season="rabi",
        candidates=["boro_rice"], crop_facts=facts, climatology_by_crop=climatology,
    )
    climate = next(c for c in results[0].components if c.name == "Climate fit")
    assert 0.0 <= climate.points < 5.0


def test_climate_fit_unavailable_when_facts_present_but_climatology_missing():
    facts = {
        "boro_rice": CropFacts(
            crop="boro_rice", seasons=frozenset({"rabi"}), soil_primary=frozenset({"clay_loam"}),
            soil_secondary=frozenset(), soil_marginal=frozenset(), water_min_rank=0,
            water_need="high", temp_opt_c=(20.0, 35.0), rain_opt_mm=(0.0, 500.0),
            growing_months=frozenset({1, 2, 3}),
        ),
    }
    results = score_crops(
        district=RAJSHAHI, soil_type="clay_loam", water_source="tubewell", season="rabi",
        candidates=["boro_rice"], crop_facts=facts, climatology_by_crop=None,
    )
    climate = next(c for c in results[0].components if c.name == "Climate fit")
    assert climate.points == 0.0 and climate.provenance.confidence == "low"


# ── Stability / CV ────────────────────────────────────────────────────────────
def test_district_cv_helper():
    assert _district_cv([{"yield_kg_ha": 100.0}]) is None  # <2 points
    assert _district_cv([{"yield_kg_ha": 100.0}, {"yield_kg_ha": 100.0}]) == 0.0
    cv = _district_cv([{"yield_kg_ha": 90.0}, {"yield_kg_ha": 110.0}])
    assert cv > 0.0


def test_stability_uses_real_rajshahi_history():
    results = score_crops(
        district=RAJSHAHI, soil_type="clay_loam", water_source="tubewell", season="rabi",
        candidates=["boro_rice"],
    )
    stability = next(c for c in results[0].components if c.name == "Stability")
    assert 0.0 < stability.points <= 10.0
    assert stability.provenance.confidence == "medium"
    assert "CV=" in stability.provenance.formula


# ── District track record ─────────────────────────────────────────────────────
def test_district_track_record_uses_real_rajshahi_data():
    results = score_crops(
        district=RAJSHAHI, soil_type="clay_loam", water_source="tubewell", season="rabi",
        candidates=["boro_rice"],
    )
    tr = next(c for c in results[0].components if c.name == "District track record")
    assert 0.0 <= tr.points <= 20.0
    assert "percentile" in tr.provenance.formula


def test_no_data_district_track_record_is_unavailable():
    # Cox's Bazar has zero lentil rows in agribase_clean.db (confirmed) — the
    # "no data" exclusion only fires for crops with NO entry in CANON_TO_KEY,
    # so lentil still survives Stage 1 here; District track record must instead
    # report unavailable rather than fabricate a percentile.
    results = score_crops(
        district="Cox's Bazar", soil_type="clay_loam", water_source="tubewell", season="rabi",
        candidates=["lentil"],
    )
    c = results[0]
    assert c.excluded is False
    tr = next(comp for comp in c.components if comp.name == "District track record")
    assert tr.points == 0.0
    assert tr.provenance.confidence == "low"
    assert tr.provenance.value == "unavailable"


# ── risk_level ─────────────────────────────────────────────────────────────
def test_risk_level_helper_terciles_and_fallback():
    # >=3 known CVs: rank-based terciles
    known = [0.05, 0.10, 0.15, 0.20, 0.30]
    assert _risk_level(0.05, known) == "low"
    assert _risk_level(0.30, known) == "high"
    # <3 known: fixed thresholds
    assert _risk_level(0.05, []) == "low"
    assert _risk_level(0.15, []) == "medium"
    assert _risk_level(0.25, []) == "high"
    assert _risk_level(None, known) == "high"  # unknown -> conservative


def test_risk_level_reflects_real_rajshahi_stability_spread():
    results = score_crops(
        district=RAJSHAHI, soil_type="clay_loam", water_source="tubewell", season="rabi",
        candidates=ALL_5,
    )
    by_crop = _by_crop(results)
    # potato has the lowest CV (~0.006) at Rajshahi among the 5 -> low risk
    assert by_crop["potato"].risk_level == "low"


# ── determinism ────────────────────────────────────────────────────────────
def test_determinism_same_inputs_same_output(monkeypatch):
    # `now=` fixes the scorer's own timestamps, but the provenance it derives
    # from cropdb results carries THEIR read time, stamped to the second at
    # each call. Two runs either side of a second boundary then differ on a
    # field that has nothing to do with scoring — a flake that shows up only
    # under a full suite, i.e. exactly at a merge gate. Freeze the read clock
    # so the assertion stays about determinism of the ranking.
    import backend.tools.cropdb as cropdb

    monkeypatch.setattr(cropdb, "_now", lambda: "2026-07-24T00:00:00+00:00")

    kwargs = dict(district=RAJSHAHI, soil_type="clay_loam", water_source="tubewell",
                   season="rabi", candidates=ALL_5, now="2026-07-24T00:00:00+00:00")
    r1 = score_crops(**kwargs)
    r2 = score_crops(**kwargs)
    assert [c.model_dump() for c in r1] == [c.model_dump() for c in r2]


# ── no network dependency (structural + behavioral) ──────────────────────────
def test_pure_core_has_no_network_imports():
    assert not hasattr(cs, "httpx")
    assert not hasattr(cs, "get_climatology")


def test_pure_core_succeeds_even_if_httpx_is_broken(monkeypatch):
    # Simulate httpx being entirely unusable; score_crops must be unaffected
    # since it never touches the network directly.
    broken = types.ModuleType("httpx")

    def _raise(*a, **k):
        raise RuntimeError("network should never be touched by score_crops")

    broken.Client = _raise  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "httpx", broken)
    results = score_crops(
        district=RAJSHAHI, soil_type="clay_loam", water_source="tubewell", season="rabi",
        candidates=["boro_rice"],
    )
    assert results and results[0].crop == "boro_rice"


# ── provenance completeness (schema rule 3) ──────────────────────────────────
def test_every_component_and_exclusion_has_provenance():
    results = score_crops(
        district=RAJSHAHI, soil_type="clay_loam", water_source="tubewell", season="rabi",
        candidates=[*ALL_5, "wheat"],
    )
    for c in results:
        if c.excluded:
            if c.crop != "wheat":
                assert c.provenance, f"{c.crop} exclusion missing provenance"
        else:
            for comp in c.components:
                assert comp.provenance is not None
                assert comp.provenance.retrieved_at


# ── agent tool wrapper ────────────────────────────────────────────────────────
def test_crop_scorer_tool_returns_candidates_and_degraded_list():
    # As of 2026-07-24, data/prices.md carries real prices+costs for all 5 crops,
    # so the finance seam is live and only the KB (crop_facts) gaps remain
    # degraded: season/soil/water screening, Agronomic fit, Climate fit.
    out = cs.crop_scorer_tool(district=RAJSHAHI, soil_type="clay_loam",
                              water_source="tubewell", season="rabi")
    assert "candidates" in out and len(out["candidates"]) == 5
    assert "degraded" in out and len(out["degraded"]) == 3
    assert not any("Profit" in d for d in out["degraded"])
    assert all(isinstance(d, str) for d in out["degraded"])
    # Profit component itself must now be real, not "unavailable".
    for c in out["candidates"]:
        if c["excluded"]:
            continue
        profit = next(comp for comp in c["components"] if comp["name"] == "Profit")
        assert profit["max"] == 25.0
        assert profit["provenance"]["value"] != "unavailable"


def test_crop_scorer_tool_never_raises_on_bad_input():
    out = cs.crop_scorer_tool(district="Nowhere", soil_type="clay_loam",
                              water_source="tubewell", season="rabi")
    assert "error" in out or "candidates" in out  # degrades, never crashes
