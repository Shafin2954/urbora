"""Shared fixtures.

The big one is `priced_md`: a `prices.md` with every crop costed. Today the
real file's farm-gate table is empty on purpose (the yearbook extraction is
still running), so without this fixture nothing downstream of prices would ever
be exercised — and "it will work once the data lands" would be an untested
claim about the most accuracy-critical path in the product.

Every number in it is an ARBITRARY TEST VALUE with a fake citation. It must
never be mistaken for curated agricultural data, which is why the source_title
says so on every row.
"""

import pytest

PRICED_MD = """
## 1. Selling price — farm-gate (what the FARMER receives)

| crop | price_bdt_per_kg | basis | source_id | source_title | locator | date | confidence |
|---|---|---|---|---|---|---|---|
| boro_rice | 30 | paddy | test.fixture | Test fixture — not real data | p.1 | 2024 | medium |
| aman_rice | 28 | paddy | test.fixture | Test fixture — not real data | p.1 | 2024 | medium |
| potato | 18 | tuber | test.fixture | Test fixture — not real data | p.1 | 2024 | medium |
| mustard | 65 | seed | test.fixture | Test fixture — not real data | p.1 | 2024 | medium |
| lentil | 95 | seed | test.fixture | Test fixture — not real data | p.1 | 2024 | medium |

## 2. Input costs — per hectare

| crop | item | qty_per_ha | unit | unit_cost_bdt | source_id | source_title | locator | date | confidence |
|---|---|---|---|---|---|---|---|---|---|
| boro_rice | Seed | 60 | kg | 50 | test.fixture | Test fixture — not real data | p.2 | 2024 | medium |
| boro_rice | Urea | 200 | kg | 27 | test.fixture | Test fixture — not real data | p.2 | 2024 | medium |
| boro_rice | Labour | 120 | person-day | 600 | test.fixture | Test fixture — not real data | p.2 | 2024 | medium |
| aman_rice | Seed | 50 | kg | 48 | test.fixture | Test fixture — not real data | p.2 | 2024 | medium |
| aman_rice | Labour | 100 | person-day | 600 | test.fixture | Test fixture — not real data | p.2 | 2024 | medium |
| potato | Seed tuber | 1500 | kg | 25 | test.fixture | Test fixture — not real data | p.2 | 2024 | medium |
| potato | Labour | 150 | person-day | 600 | test.fixture | Test fixture — not real data | p.2 | 2024 | medium |
| mustard | Seed | 8 | kg | 120 | test.fixture | Test fixture — not real data | p.2 | 2024 | medium |
| mustard | Labour | 60 | person-day | 600 | test.fixture | Test fixture — not real data | p.2 | 2024 | medium |
| lentil | Seed | 40 | kg | 110 | test.fixture | Test fixture — not real data | p.2 | 2024 | medium |
| lentil | Labour | 55 | person-day | 600 | test.fixture | Test fixture — not real data | p.2 | 2024 | medium |
"""

# Rajshahi has real crop.db projections for all five crops (PRD §3.3 demo
# district), so tests using it exercise a genuine yield join — only the money
# side is fixtured.
DEMO_DISTRICT = "Rajshahi"


@pytest.fixture
def priced_md(tmp_path):
    """Path to a prices.md where every crop is fully costed."""
    path = tmp_path / "prices.md"
    path.write_text(PRICED_MD, encoding="utf-8")
    return path


@pytest.fixture
def priced_catalog(priced_md):
    from backend.finance.catalog import PriceCatalog

    return PriceCatalog(priced_md)


@pytest.fixture(autouse=True)
def _hermetic_providers(monkeypatch):
    """A developer's real keys in .env.local must not switch providers in tests."""
    from backend.tests.conftest import PROVIDER_VARS
    for var in PROVIDER_VARS:
        monkeypatch.delenv(var, raising=False)
