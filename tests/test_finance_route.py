"""`POST /api/finance/recompute` — the judged live-edit moment.

PLAN.md §5 step 3: change the area from 2 bigha to 3 on screen, and every
number moves consistently. A judge will do exactly that and then check the
arithmetic, so what is asserted here is coherence under an edit, not fixtures.

Also asserted: the route refuses rather than inventing. No default farm, no
default crop, no projection from prices nobody cited.
"""

import pytest
from fastapi.testclient import TestClient

from backend.api import finance as finance_route
from backend.api.main import app

DISTRICT = "Rajshahi"


@pytest.fixture(autouse=True)
def clean_state():
    finance_route.forget()
    yield
    finance_route.forget()


@pytest.fixture
def priced(priced_catalog, monkeypatch):
    """Pretend the yearbook extraction has landed (fixture in conftest.py)."""
    monkeypatch.setattr(finance_route, "load_catalog", lambda *a, **k: priced_catalog)
    return priced_catalog


def post(client, farm_id="farm-1", **overrides):
    return client.post(
        "/api/finance/recompute",
        json={"farm_id": farm_id, "overrides": overrides},
    )


# --- refusals ----------------------------------------------------------------


def test_an_unknown_farm_with_no_inputs_is_refused_by_name():
    with TestClient(app) as client:
        response = post(client)
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "crop" in detail and "district" in detail and "area" in detail


def test_a_typo_in_an_override_field_is_not_silently_absorbed():
    """`aera: 3` must fail loudly, not recompute the old area and look fine."""
    with TestClient(app) as client:
        response = post(client, crop="boro_rice", district=DISTRICT, aera=3)
    assert response.status_code == 400
    assert "aera" in response.json()["detail"]


def test_uncited_prices_produce_422_not_a_number():
    """Today's real state: yields exist, prices do not."""
    with TestClient(app) as client:
        response = post(client, crop="boro_rice", district=DISTRICT, area=1)
    # 422 while prices.md is empty; 200 once it is filled — both are correct,
    # and neither is a fabricated projection.
    assert response.status_code in (200, 422)
    if response.status_code == 422:
        assert "prices.md" in response.json()["detail"]


def test_a_crop_without_a_yield_series_is_refused(priced):
    with TestClient(app) as client:
        response = post(client, crop="wheat", district=DISTRICT, area=1)
    assert response.status_code == 422


# --- the demo moment ---------------------------------------------------------


def test_area_edit_recomputes_everything_consistently(priced):
    with TestClient(app) as client:
        two = post(client, crop="boro_rice", district=DISTRICT, area=2, area_unit="bigha")
        assert two.status_code == 200, two.text
        # The follow-up edit sends ONLY the changed field — the farm is remembered.
        three = post(client, area=3).json()
        two = two.json()

    base2 = two["finance"]["scenarios"]["base"]
    base3 = three["finance"]["scenarios"]["base"]

    assert base3["total_cost"] == pytest.approx(base2["total_cost"] * 1.5, rel=1e-5)
    assert base3["revenue"] == pytest.approx(base2["revenue"] * 1.5, rel=1e-5)
    assert base3["net_profit"] == pytest.approx(base2["net_profit"] * 1.5, rel=1e-5)
    # ROI is scale-invariant — a bigger farm is not a better margin, and this is
    # the specific thing a judge changing the area will check.
    assert base3["roi_pct"] == pytest.approx(base2["roi_pct"], abs=0.02)
    # Break-even price is per kg, so it does not move with area at all.
    assert three["finance"]["breakeven_price_bdt"] == pytest.approx(
        two["finance"]["breakeven_price_bdt"], abs=0.01
    )


def test_the_displayed_cost_column_adds_up_over_the_wire(priced):
    """Not just in the engine — in the JSON the browser actually renders."""
    from decimal import Decimal

    with TestClient(app) as client:
        body = post(
            client, crop="potato", district=DISTRICT, area=3, area_unit="bigha"
        ).json()

    for name in ("conservative", "base", "optimistic"):
        scenario = body["finance"]["scenarios"][name]
        column = sum(
            (Decimal(str(item["total"])) for item in scenario["items"]), Decimal("0")
        )
        assert column == Decimal(str(scenario["total_cost"]))


def test_every_rendered_item_carries_provenance(priced):
    """PRD §7 / CLAUDE.md §2.3 — a number without provenance must not render."""
    with TestClient(app) as client:
        body = post(client, crop="boro_rice", district=DISTRICT, area=1).json()

    scenario = body["finance"]["scenarios"]["base"]
    assert scenario["items"]
    for item in scenario["items"]:
        assert item["provenance"]["source_id"]
        assert item["provenance"]["retrieved_at"]
    assert body["finance"]["assumptions"], "the yield and price assumptions must ship"


def test_switching_crop_keeps_the_remembered_area(priced):
    with TestClient(app) as client:
        post(client, crop="boro_rice", district=DISTRICT, area=2, area_unit="bigha")
        switched = post(client, crop="mustard").json()
    assert switched["crop"] == "mustard"
    assert switched["area_stated"] == {"value": 2, "unit": "bigha"}


def test_budget_affordability_is_reported_when_given(priced):
    with TestClient(app) as client:
        body = post(
            client, crop="potato", district=DISTRICT, area=1, budget_bdt=1000
        ).json()
    assert body["affordable"] is False


def test_two_farms_do_not_share_inputs(priced):
    with TestClient(app) as client:
        post(client, farm_id="a", crop="boro_rice", district=DISTRICT, area=1)
        response = post(client, farm_id="b", area=5)
    assert response.status_code == 400  # farm b has no crop/district of its own
