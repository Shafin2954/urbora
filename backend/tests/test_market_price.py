"""market_price — unit conversion, the sell/store rule, and its disclaimers.

These run against the real agristats.db because that database ships with the
repo and is the whole point of the tool; a stubbed price series would test the
arithmetic and not the mapping, and the mapping (which commodity row means
"potato") is the part that can silently be wrong.
"""

from __future__ import annotations

import pytest

from backend.tools.market_price import _COMMODITY, _DB, market_price

pytestmark = pytest.mark.skipif(not _DB.exists(), reason="agristats.db not present")

CROPS = sorted(_COMMODITY)


@pytest.mark.parametrize("crop", CROPS)
def test_every_supported_crop_resolves_to_real_price_history(crop):
    result = market_price(crop)
    assert "error" not in result, result
    assert result["observations"] > 50
    assert result["years_covered"]


@pytest.mark.parametrize("crop", CROPS)
def test_prices_are_per_kg_not_per_quintal(crop):
    """The source is Taka/Quintal. Forgetting the /100 is a 100x error."""
    result = market_price(crop)
    priced = [row["avg_price_bdt_per_kg"] for row in result["monthly_curve"] if row["avg_price_bdt_per_kg"]]
    assert priced
    # No Bangladeshi staple wholesales below 1 Tk/kg or above 500 Tk/kg.
    assert all(1 < value < 500 for value in priced), priced


def test_curve_covers_all_twelve_months():
    curve = market_price("potato")["monthly_curve"]
    assert [row["month"] for row in curve] == list(range(1, 13))


def test_a_meaningful_later_peak_reads_as_store():
    """Potato bottoms out at the Feb-March harvest and peaks late in the year."""
    result = market_price("potato", month=3)
    assert result["verdict"] == "consider_storing"
    assert result["expected_gain_pct"] > 5
    assert result["best_later_month"]


def test_no_later_upside_reads_as_sell_now():
    """December has no later month left in the year, so there is nothing to wait for."""
    result = market_price("potato", month=12)
    assert result["verdict"] == "sell_now"


@pytest.mark.parametrize("crop", CROPS)
def test_output_cannot_be_mistaken_for_a_forecast_or_for_income(crop):
    result = market_price(crop)
    assert result["basis"] == "historical_pattern"
    assert result["not_a_forecast"] is True
    # Wholesale must never be presented as the farmer's revenue — that path
    # belongs to data/prices.md's farm-gate table alone.
    assert result["is_farm_gate"] is False
    assert result["price_type"] == "wholesale"
    # Storage cost is unsourced, so it is withheld rather than estimated.
    assert result["storage_cost_bdt"] is None


def test_unsupported_crop_is_reported_not_guessed():
    result = market_price("wheat")
    assert result["error"] == "unsupported_crop"


def test_paddy_not_milled_rice_is_used_for_the_rice_crops():
    """prices.md prices PADDY; a milled-rice series would be a different, dearer
    commodity wearing the same crop name."""
    for crop in ("boro_rice", "aman_rice"):
        assert market_price(crop)["commodity"].startswith("Paddy")
