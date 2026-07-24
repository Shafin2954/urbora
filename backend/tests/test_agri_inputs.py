"""Chapter 7 input-statistics tool: fixed queries, outlier filtering, provenance."""

from backend.tools.agri_inputs import agri_inputs


def _assert_provenance(result: dict) -> None:
    assert result["source_type"] == "dataset"
    assert result["source_id"] == "agristats_ch7_agricultural_inputs"
    assert "agristats.db :: v_" in result["locator"]
    assert result.get("reference_year") or result.get("calendar_year") or result.get("period")


def test_seed_supply_is_cited_and_crop_mapped():
    result = agri_inputs("seed_supply", crop="boro_rice")
    assert result["dataset_crop"] == "Rice"
    assert result["seed_supply_metric_tons"] >= 0
    _assert_provenance(result)


def test_fertilizer_and_pesticide_return_historical_not_price_facts():
    fertilizer = agri_inputs("fertilizer_market", fertilizer_type="Urea")
    assert fertilizer["sales_metric_tons"] >= 0
    _assert_provenance(fertilizer)

    pesticide = agri_inputs("pesticide_use")
    assert pesticide["total_consumption_metric_tons"] >= 0
    _assert_provenance(pesticide)


def test_irrigation_method_is_cited_and_sorted():
    result = agri_inputs("irrigation_method", crop="boro_rice")
    assert result["methods"]
    assert result["methods"] == sorted(result["methods"], key=lambda row: row["area_acres"], reverse=True)
    _assert_provenance(result)


def test_unknown_action_is_safe():
    result = agri_inputs("select * from v_seed")
    assert "error" in result
    assert "seed_supply" in result["actions"]
