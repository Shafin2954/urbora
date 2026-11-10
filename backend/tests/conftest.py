"""Shared test setup for the whole suite (backend/tests).

1. Hermetic providers: a developer's real keys in .env.local must not switch
   providers (e.g. send test audio to Sarvam) or turn on live channels.
2. `priced_md` / `priced_catalog`: a prices.md with every crop costed. Every
   number in it is an ARBITRARY TEST VALUE with a fake citation, never curated
   agricultural data; the source_title says so on every row.
"""

import pytest

PROVIDER_VARS = (
    "SARVAM_API_KEY", "AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "VOICE_STT", "VOICE_TTS",
    "SMS_PROVIDER", "SMSGATE_URL", "SMSGATE_USER", "SMSGATE_PASSWORD", "SMSGATE_SIGNING_KEY",
    "CHANNEL_EMULATOR_ENABLED", "ALERT_SMS_ENABLED", "BRIDGE_TOKEN", "PHONELINK_ENABLED",
)


@pytest.fixture(autouse=True)
def _hermetic_providers(monkeypatch):
    for var in PROVIDER_VARS:
        monkeypatch.delenv(var, raising=False)


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
