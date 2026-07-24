"""Tests for backend/finance/catalog.py's `cost_basis` column (2026-07-25).

Scoring-defect fix: mustard/lentil in the real data/prices.md carry a
fertiliser-only (partial) cost basis, structurally different from boro/aman/
potato's BBS complete aggregate expenditure. `PriceCatalog` must parse and
expose that distinction so crop_scorer can stop min-max normalizing a Profit
component across incomparable cost bases (see backend/tests/test_crop_scorer.py
for the scorer-side tests).
"""

from __future__ import annotations

import textwrap

import pytest

from backend.finance.catalog import PriceCatalog

_MD = textwrap.dedent(
    """\
    # test prices

    ## 1. Selling price — farm-gate (what the FARMER receives)

    | crop | price_bdt_per_kg | basis | source_id | source_title | locator | date | confidence |
    |---|---|---|---|---|---|---|---|
    | boro_rice | 30.0 | paddy | t | t | t | 2026-01-01 | medium |
    | lentil | 90.0 | raw seed | t | t | t | 2026-01-01 | medium |

    ## 2. Input costs — per hectare

    | crop | item | qty_per_ha | unit | unit_cost_bdt | cost_basis | source_id | source_title | locator | date | confidence |
    |---|---|---|---|---|---|---|---|---|---|---|
    | boro_rice | Total cultivation cost | 1 | ha | 90000 | complete | t | t | t | 2026-01-01 | medium |
    | lentil | Urea | 42.5 | kg | 27 | partial_fertilizer_only | t | t | t | 2026-01-01 | low |

    ## 3. Retail market context — NOT a farmer's selling price

    | commodity | related_crop | price_min_bdt_per_kg | price_max_bdt_per_kg | note |
    |---|---|---|---|---|
    """
)

_MD_NO_COLUMN = _MD.replace(" | cost_basis", "").replace(" | complete", "").replace(
    " | partial_fertilizer_only", ""
)


@pytest.fixture()
def catalog(tmp_path):
    p = tmp_path / "prices.md"
    p.write_text(_MD, encoding="utf-8")
    return PriceCatalog(p)


def test_cost_basis_parsed_per_crop(catalog):
    assert catalog.cost_basis("boro_rice") == "complete"
    assert catalog.cost_basis("lentil") == "partial_fertilizer_only"


def test_cost_basis_defaults_to_complete_when_column_absent(tmp_path):
    p = tmp_path / "prices.md"
    p.write_text(_MD_NO_COLUMN, encoding="utf-8")
    cat = PriceCatalog(p)
    # Backward compatible: a crop that predates this column is treated as
    # "complete" rather than silently losing its Profit score.
    assert cat.cost_basis("boro_rice") == "complete"
    assert cat.cost_basis("lentil") == "complete"


def test_cost_basis_defaults_to_complete_for_unknown_crop(catalog):
    assert catalog.cost_basis("mustard") == "complete"


def test_scorer_finance_carries_cost_basis_through(catalog):
    finance, gap = catalog.scorer_finance(
        ["boro_rice", "lentil"], {"boro_rice": 4300.0, "lentil": 900.0}
    )
    assert gap is None
    assert finance["boro_rice"]["cost_basis"] == "complete"
    assert finance["lentil"]["cost_basis"] == "partial_fertilizer_only"
