"""prices.md -> finance inputs.

The catalog is where "no invented data" stops being a slogan. These tests pin
the three behaviours that make it true:

  - an absent row produces a refusal, not a zero and not a guess
  - retail prices cannot reach a projection, however convenient that would be
  - partial price coverage does not silently rank the uncited crops down

The fixture tables below are ARBITRARY TEST VALUES with fake citations. Real
prices live in data/prices.md; nothing here is a claim about any market.
"""

import pytest

from backend.finance import PriceDataUnavailable
from backend.finance.catalog import PRICES_MD, PriceCatalog
from backend.schemas import Provenance

YIELD_PROV = Provenance(
    value=4000,
    unit="kg/ha",
    source_type="dataset",
    source_id="crop.db",
    source_title="Test fixture — not real data",
    retrieved_at="2026-07-24T09:00:00+00:00",
    confidence="low",
)


def write(tmp_path, body: str):
    path = tmp_path / "prices.md"
    path.write_text(body, encoding="utf-8")
    return PriceCatalog(path)


FULL = """
## 1. Selling price — farm-gate (what the FARMER receives)

| crop | price_bdt_per_kg | basis | source_id | source_title | locator | date | confidence |
|---|---|---|---|---|---|---|---|
| boro_rice | 30.00 | paddy | test.fixture | Test fixture | Table X p.1 | 2024-12-31 | medium |
| potato | 18.00 | tuber | test.fixture | Test fixture | Table X p.2 | 2024-12-31 | medium |

## 2. Input costs — per hectare

| crop | item | qty_per_ha | unit | unit_cost_bdt | source_id | source_title | locator | date | confidence |
|---|---|---|---|---|---|---|---|---|---|
| boro_rice | Seed | 60 | kg | 50 | test.fixture | Test fixture | p.3 | 2024-12-31 | medium |
| boro_rice | Urea | 200 | kg | 27 | test.fixture | Test fixture | p.3 | 2024-12-31 | medium |
| potato | Seed tuber | 1500 | kg | 25 | test.fixture | Test fixture | p.4 | 2024-12-31 | medium |

## 3. Retail market context — NOT a farmer's selling price

| commodity | related_crop | price_min_bdt_per_kg | price_max_bdt_per_kg | note |
|---|---|---|---|---|
| coarse rice | boro_rice | 50 | 60 | milled, retail |
"""


# --- refusal beats a guess ---------------------------------------------------


def test_an_empty_file_yields_no_prices_and_names_what_is_missing(tmp_path):
    catalog = write(tmp_path, "# nothing here\n")
    assert catalog.priced_crops() == []
    assert catalog.missing_for("boro_rice") == [
        "input costs",
        "farm-gate selling price",
    ]


def test_projection_refuses_rather_than_inventing(tmp_path):
    catalog = write(tmp_path, "# nothing here\n")
    with pytest.raises(PriceDataUnavailable) as caught:
        catalog.projection(
            "boro_rice",
            area_ha=1.0,
            base_yield_kg_ha=4000.0,
            band_kg_ha=500.0,
            yield_provenance=YIELD_PROV,
        )
    assert "farm-gate selling price" in caught.value.missing


def test_a_blank_price_cell_means_absent_not_zero(tmp_path):
    """A zero price is a claim — that the crop is worthless. Blank is not."""
    catalog = write(
        tmp_path,
        """
## 1. Selling price — farm-gate (what the FARMER receives)

| crop | price_bdt_per_kg | basis | source_id | source_title | locator | date | confidence |
|---|---|---|---|---|---|---|---|
| boro_rice |  | paddy | test.fixture | Test fixture | p.1 | 2024 | medium |
""",
    )
    assert catalog.price("boro_rice") is None


def test_unknown_crop_keys_are_ignored_not_guessed(tmp_path):
    catalog = write(
        tmp_path,
        """
## 1. Selling price — farm-gate (what the FARMER receives)

| crop | price_bdt_per_kg | basis | source_id | source_title | locator | date | confidence |
|---|---|---|---|---|---|---|---|
| dragonfruit | 400 | fruit | test.fixture | Test fixture | p.1 | 2024 | medium |
""",
    )
    assert catalog.price("dragonfruit") is None
    assert catalog.priced_crops() == []


# --- retail is structurally unreachable from revenue -------------------------


def test_retail_rows_parse_but_never_price_a_projection(tmp_path):
    """The whole point: retail is visible, and cannot become revenue."""
    catalog = write(
        tmp_path,
        """
## 2. Input costs — per hectare

| crop | item | qty_per_ha | unit | unit_cost_bdt | source_id | source_title | locator | date | confidence |
|---|---|---|---|---|---|---|---|---|---|
| boro_rice | Seed | 60 | kg | 50 | test.fixture | Test fixture | p.3 | 2024 | medium |

## 3. Retail market context — NOT a farmer's selling price

| commodity | related_crop | price_min_bdt_per_kg | price_max_bdt_per_kg | note |
|---|---|---|---|---|
| coarse rice | boro_rice | 50 | 60 | milled, retail |
""",
    )
    assert len(catalog.retail) == 1
    assert catalog.retail[0].price_max_bdt_per_kg == 60
    # Costs are present, so the only thing missing is the farm-gate price —
    # and the retail row sitting right there does not fill it.
    assert catalog.missing_for("boro_rice") == ["farm-gate selling price"]
    with pytest.raises(PriceDataUnavailable):
        catalog.projection(
            "boro_rice",
            area_ha=1.0,
            base_yield_kg_ha=4000.0,
            band_kg_ha=500.0,
            yield_provenance=YIELD_PROV,
        )


# --- the happy path ----------------------------------------------------------


def test_a_complete_crop_projects_with_price_provenance(tmp_path):
    catalog = write(tmp_path, FULL)
    assert catalog.priced_crops() == ["boro_rice", "potato"]

    result = catalog.projection(
        "boro_rice",
        area_ha=1.0,
        base_yield_kg_ha=4000.0,
        band_kg_ha=500.0,
        yield_provenance=YIELD_PROV,
    )
    base = result.scenarios.base
    assert base.total_cost == 60 * 50 + 200 * 27      # 8,400
    assert base.revenue == 4000 * 30.0                 # 120,000
    assert base.net_profit == 120_000 - 8_400

    # Every assumption is citable — the price one carries its locator.
    price_prov = next(a for a in result.assumptions if a.source_id == "test.fixture")
    assert price_prov.locator == "Table X p.1"
    assert price_prov.confidence == "medium"


def test_cost_lines_carry_their_own_provenance(tmp_path):
    catalog = write(tmp_path, FULL)
    lines = catalog.cost_lines("boro_rice")
    assert [line.name for line in lines] == ["Seed", "Urea"]
    for line in lines:
        assert line.provenance.source_id == "test.fixture"
        assert line.provenance.source_type == "static_table"


def test_columns_are_matched_by_name_not_position(tmp_path):
    """A curator reordering columns must not shift every value one to the left."""
    catalog = write(
        tmp_path,
        """
## 1. Selling price — farm-gate (what the FARMER receives)

| source_id | crop | confidence | price_bdt_per_kg | basis | source_title | locator | date |
|---|---|---|---|---|---|---|---|
| test.fixture | mustard | high | 65.5 | seed | Test fixture | p.9 | 2024 |
""",
    )
    row = catalog.price("mustard")
    assert row is not None
    assert row.price_bdt_per_kg == 65.5
    assert row.confidence == "high"


# --- the scorer seam ---------------------------------------------------------


def test_scorer_finance_is_all_or_nothing(tmp_path):
    """Partial coverage would rank uncited crops down for lacking a citation."""
    catalog = write(tmp_path, FULL)
    yields = {"boro_rice": 4000.0, "potato": 20000.0, "mustard": 1200.0}

    finance, reason = catalog.scorer_finance(["boro_rice", "potato"], yields)
    assert reason is None
    assert set(finance) == {"boro_rice", "potato"}

    # mustard has no rows at all — so nobody gets a profit score.
    finance, reason = catalog.scorer_finance(["boro_rice", "potato", "mustard"], yields)
    assert finance is None
    assert "mustard" in reason


def test_scorer_finance_matches_the_engine(tmp_path):
    """The scorer's budget filter and the projection must never disagree."""
    catalog = write(tmp_path, FULL)
    finance, _ = catalog.scorer_finance(["boro_rice"], {"boro_rice": 4000.0})

    one_ha = catalog.projection(
        "boro_rice",
        area_ha=1.0,
        base_yield_kg_ha=4000.0,
        band_kg_ha=0.0,
        yield_provenance=YIELD_PROV,
    )
    assert finance["boro_rice"]["min_cost_per_ha"] == one_ha.scenarios.base.total_cost
    assert finance["boro_rice"]["net_profit_bdt_per_ha"] == pytest.approx(
        one_ha.scenarios.base.net_profit
    )


def test_a_missing_yield_blocks_the_profit_component(tmp_path):
    """No yield means no revenue; refusing beats assuming an average."""
    catalog = write(tmp_path, FULL)
    finance, reason = catalog.scorer_finance(["boro_rice", "potato"], {"boro_rice": 4000.0})
    assert finance is None
    assert "potato" in reason


# --- the real file -----------------------------------------------------------


def test_the_shipped_prices_file_parses(tmp_path):
    """data/prices.md must always be readable, even while its tables are empty.

    Its farm-gate table is deliberately empty until the yearbook extraction
    lands, so this asserts the *shape* holds — not that any crop is priced.
    """
    catalog = PriceCatalog(PRICES_MD)
    assert catalog.retail, "the TCB retail rows should parse"
    for crop in ("boro_rice", "aman_rice", "potato", "mustard", "lentil"):
        # Whatever the current state of curation, asking must never raise.
        assert isinstance(catalog.missing_for(crop), list)


def test_the_shipped_retail_rows_are_not_reachable_as_revenue():
    """The live file's retail rows exist; no crop may be priced from them.

    data/prices.md now carries real farm-gate prices (agristats.db, 2026-07-24
    curation), so "price is missing" is no longer the invariant to check.
    Checking farm-gate price against the retail band numerically is unsound —
    lentil's real farm-gate price (90.78, raw Masur) coincidentally falls inside
    the unrelated retail split-dal band (90-100) despite being a different
    commodity, so a numeric-overlap check can fail on a true positive. The
    invariant that actually matters is structural: removing the retail section
    entirely must not change any farm-gate price or cost-completeness result,
    proving `price()`/`projection()` never reads `self.retail`.
    """
    catalog = PriceCatalog(PRICES_MD)
    related = {row.related_crop for row in catalog.retail}
    assert related & {"boro_rice", "potato", "lentil"}, "retail covers real crops"

    text = PRICES_MD.read_text(encoding="utf-8")
    retail_heading = "## 3. Retail market context"
    assert retail_heading in text
    stripped_text = text[: text.index(retail_heading)]
    stripped_path = PRICES_MD.parent / "_test_prices_no_retail.md"
    stripped_path.write_text(stripped_text, encoding="utf-8")
    try:
        no_retail_catalog = PriceCatalog(stripped_path)
        assert no_retail_catalog.retail == []
        for crop in ("boro_rice", "aman_rice", "potato", "mustard", "lentil"):
            assert no_retail_catalog.price(crop) == catalog.price(crop)
            assert no_retail_catalog.missing_for(crop) == catalog.missing_for(crop)
    finally:
        stripped_path.unlink(missing_ok=True)
