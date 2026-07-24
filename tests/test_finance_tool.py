"""The agent's `finance_projection` tool, and the data-drop it is waiting for.

Today `data/prices.md` has no farm-gate rows, so this tool refuses to cost
anything. That refusal is the feature — but it also means nothing downstream is
exercised, and "it will work when the prices land" is exactly the kind of claim
that turns out to be false at 4am.

So these tests fill a price table and assert the whole chain lights up:
tool → catalog → engine → scorer Profit component → Budget exclusion. If the
yearbook extraction lands and something is still broken, it will be broken here
first, not on stage.

The fixture prices are ARBITRARY TEST VALUES with fake citations.
"""

import pytest

from backend.finance.catalog import PriceCatalog
from backend.tools import crop_scorer as scorer_module
from backend.tools import finance as finance_module

# Rajshahi has real crop.db projections for all five crops (PRD §3.3 demo
# district), so the yield half of every join below is genuine — only the money
# is fixtured. The full priced table lives in conftest.py.
DISTRICT = "Rajshahi"


@pytest.fixture
def priced(priced_catalog, monkeypatch):
    """Pretend the yearbook extraction has landed."""
    import backend.finance as finance_pkg

    monkeypatch.setattr(finance_module, "load_catalog", lambda *a, **k: priced_catalog)
    monkeypatch.setattr(finance_pkg, "load_catalog", lambda *a, **k: priced_catalog)
    return priced_catalog


# --- today: refusal ----------------------------------------------------------


def test_without_prices_the_tool_refuses_but_still_reports_the_yield():
    """The yield half of the join is real today; only the money is missing.

    Reporting it proves the refusal is about prices, not about a broken tool.
    """
    out = finance_module.finance_projection(
        crop="boro_rice", district=DISTRICT, area=2, area_unit="bigha"
    )
    if out.get("error") == "price_data_unavailable":
        assert "farm-gate selling price" in out["missing"]
        assert out["yield_available"]["base_yield_kg_ha"] > 0
        assert out["yield_available"]["band_kg_ha"] >= 0
    else:  # prices have landed — then it must be a real projection
        assert out["summary"]["total_cost_bdt"] > 0


def test_a_crop_with_no_yield_series_is_refused_not_estimated():
    out = finance_module.finance_projection(crop="wheat", district=DISTRICT, area=1)
    assert "no yield data" in out["error"]


def test_an_unknown_area_unit_is_an_error_not_a_silent_hectare():
    out = finance_module.finance_projection(
        crop="boro_rice", district=DISTRICT, area=2, area_unit="football pitches"
    )
    assert "unknown area unit" in out["error"]


# --- after the data drop -----------------------------------------------------


def test_the_tool_costs_a_farm_once_prices_exist(priced):
    out = finance_module.finance_projection(
        crop="boro_rice", district=DISTRICT, area=2, area_unit="bigha"
    )
    assert "error" not in out
    summary = out["summary"]
    assert summary["total_cost_bdt"] > 0
    assert summary["revenue_bdt"] > 0
    assert summary["breakeven_price_bdt_per_kg"] > 0
    # The band travels with the yield, so a narration cannot quote one alone.
    assert out["yield_band_kg_ha"] >= 0
    assert out["yield_n_points"] >= 1
    # 2 bigha, converted once, here — not by the model.
    assert out["area_ha"] == pytest.approx(0.2676, abs=1e-4)


def test_all_three_scenarios_reach_the_agent(priced):
    out = finance_module.finance_projection(
        crop="potato", district=DISTRICT, area=1, area_unit="hectare"
    )
    scenarios = out["projection"]["scenarios"]
    assert set(scenarios) == {"conservative", "base", "optimistic"}
    assert (
        scenarios["conservative"]["net_profit"]
        < scenarios["base"]["net_profit"]
        < scenarios["optimistic"]["net_profit"]
    )


def test_every_cost_line_reaches_the_agent_with_provenance(priced):
    """PRD §7: a number without provenance must not render."""
    out = finance_module.finance_projection(
        crop="boro_rice", district=DISTRICT, area=1, area_unit="hectare"
    )
    items = out["projection"]["scenarios"]["base"]["items"]
    assert items
    for item in items:
        assert item["provenance"]["source_id"] == "test.fixture"
        assert item["provenance"]["source_type"] == "static_table"


def test_budget_shortfall_comes_precomputed(priced):
    """The reduced-area replan is demo recovery #2 — and the model must not
    calculate the reduced area itself (rule 1)."""
    out = finance_module.finance_projection(
        crop="potato", district=DISTRICT, area=1, area_unit="hectare", budget_bdt=1000
    )
    budget = out["budget"]
    assert budget["affordable"] is False
    assert budget["shortfall_bdt"] > 0
    assert 0 < budget["max_area_ha_within_budget"] < 1.0


def test_an_affordable_plan_reports_no_shortfall(priced):
    out = finance_module.finance_projection(
        crop="mustard", district=DISTRICT, area=1, area_unit="katha", budget_bdt=500_000
    )
    assert out["budget"]["affordable"] is True
    assert out["budget"]["shortfall_bdt"] == 0


# --- the scorer seam switching on -------------------------------------------


def test_profit_and_budget_switch_on_when_prices_land(priced):
    """The whole point of the seam: data supply, not code change."""
    before = scorer_module.crop_scorer_tool(
        district=DISTRICT, soil_type="clay_loam", water_source="tubewell", season="rabi"
    )
    profit_before = [
        c for c in before["candidates"] if not c["excluded"]
    ][0]["components"]
    profit_component = next(c for c in profit_before if c["name"] == "Profit")

    # With prices present the Profit component must actually score.
    assert profit_component["max"] == 25.0
    assert not any("Profit component" in d for d in before["degraded"]), (
        "with every candidate priced, profit must no longer be reported degraded"
    )
    assert profit_component["provenance"]["value"] != "unavailable"


PARTIAL_MD = """
## 1. Selling price — farm-gate (what the FARMER receives)

| crop | price_bdt_per_kg | basis | source_id | source_title | locator | date | confidence |
|---|---|---|---|---|---|---|---|
| boro_rice | 30 | paddy | test.fixture | Test fixture — not real data | p.1 | 2024 | medium |

## 2. Input costs — per hectare

| crop | item | qty_per_ha | unit | unit_cost_bdt | source_id | source_title | locator | date | confidence |
|---|---|---|---|---|---|---|---|---|---|
| boro_rice | Seed | 60 | kg | 50 | test.fixture | Test fixture — not real data | p.2 | 2024 | medium |
"""


def test_partial_prices_score_nobody_on_profit(tmp_path, monkeypatch):
    """A crop must never rank lower because we lack its citation."""
    partial = tmp_path / "prices.md"
    partial.write_text(PARTIAL_MD, encoding="utf-8")
    catalog = PriceCatalog(partial)
    import backend.finance as finance_pkg

    monkeypatch.setattr(finance_pkg, "load_catalog", lambda *a, **k: catalog)

    out = scorer_module.crop_scorer_tool(
        district=DISTRICT, soil_type="clay_loam", water_source="tubewell", season="rabi"
    )
    assert any("Profit component" in d for d in out["degraded"])
    for candidate in out["candidates"]:
        for component in candidate["components"]:
            if component["name"] == "Profit":
                assert component["points"] == 0.0


# --- the panel event ---------------------------------------------------------


def test_a_successful_costing_emits_a_finance_panel_event(priced):
    """The Finance tab fills from the tool's own output, not from retyped prose."""
    from backend.agent.loop import _panel_event

    result = finance_module.finance_projection(
        crop="boro_rice", district=DISTRICT, area=2, area_unit="bigha"
    )
    event = _panel_event("finance_projection", result)
    assert event is not None
    assert event.type == "finance_update"
    # Same numbers as the tool result — one computation, rendered twice.
    assert (
        event.finance.scenarios.base.total_cost
        == result["summary"]["total_cost_bdt"]
    )


def test_a_refused_costing_emits_no_panel_event():
    """An empty Finance tab is better than one showing a projection that failed."""
    from backend.agent.loop import _panel_event

    assert _panel_event("finance_projection", {"error": "price_data_unavailable"}) is None
    assert _panel_event("get_forecast", {"tmax_c": 33}) is None
    assert _panel_event("finance_projection", {"projection": {"nonsense": True}}) is None
