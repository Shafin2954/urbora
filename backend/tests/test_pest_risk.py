"""pest_risk — stage gating, weather triggering, and honest refusals.

The forecast is stubbed throughout. These tests are about the decision rules,
and a live Open-Meteo call would make them non-deterministic and offline-fragile.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.tools import pest_risk as module


def _days(n, *, tmax, tmin, precip=0.0, rh=None, start=None):
    start = start or date.today()
    return [
        {
            "date": (start + timedelta(days=i)).isoformat(),
            "tmax_c": tmax,
            "tmin_c": tmin,
            "precip_mm": precip,
            "humidity_pct": rh,
        }
        for i in range(n)
    ]


@pytest.fixture
def stub_forecast(monkeypatch):
    def _install(daily):
        monkeypatch.setattr(
            module, "get_forecast",
            lambda lat, lon, days=16: {
                "daily": daily, "source_type": "forecast", "cached": False,
            },
        )
    return _install


def _sown(days_ago: int) -> str:
    return (date.today() - timedelta(days=days_ago)).isoformat()


def test_humid_warm_weather_inside_stage_window_scores_high(stub_forecast):
    # Aman sheath blight: DAS 40-90, 25-32 C, RH >= 85. Sixteen matching days.
    stub_forecast(_days(16, tmax=32.0, tmin=26.0, rh=90.0))
    result = module.pest_risk(crop="aman_rice", district="Dinajpur", sowing_date=_sown(50))

    blight = next(r for r in result["risks"] if r["key"] == "sheath_blight")
    assert blight["status"] == "active"
    assert blight["risk_level"] == "high"
    assert blight["favourable_days"] == blight["days_checked"]
    assert result["highest_risk_level"] == "high"


def test_dry_weather_does_not_trigger_a_humidity_driven_disease(stub_forecast):
    # Same stage, same temperature band — only the humidity changes.
    stub_forecast(_days(16, tmax=32.0, tmin=26.0, rh=40.0))
    result = module.pest_risk(crop="aman_rice", district="Dinajpur", sowing_date=_sown(50))

    blight = next(r for r in result["risks"] if r["key"] == "sheath_blight")
    assert blight["risk_level"] == "low"
    assert blight["favourable_days"] == 0


def test_stage_window_gates_the_rule(stub_forecast):
    """Perfect blight weather before the crop is susceptible is still not a risk."""
    stub_forecast(_days(16, tmax=32.0, tmin=26.0, rh=90.0))
    result = module.pest_risk(crop="aman_rice", district="Dinajpur", sowing_date=_sown(2))

    blight = next(r for r in result["risks"] if r["key"] == "sheath_blight")
    assert blight["status"] == "upcoming"
    assert blight["risk_level"] is None
    assert "watch_from_date" in blight


def test_window_beyond_forecast_horizon_is_never_scored(stub_forecast):
    """NOTES #1: no invented weather past the 16-day horizon."""
    stub_forecast(_days(16, tmax=20.0, tmin=14.0, rh=90.0))
    result = module.pest_risk(crop="potato", district="Rangpur", sowing_date=_sown(0))

    assert all(r["risk_level"] is None for r in result["risks"])
    assert {r["status"] for r in result["risks"]} == {"upcoming"}


def test_missing_humidity_falls_back_to_rain_and_says_so(stub_forecast):
    stub_forecast(_days(16, tmax=32.0, tmin=26.0, precip=6.0, rh=None))
    result = module.pest_risk(crop="aman_rice", district="Dinajpur", sowing_date=_sown(50))

    assert any("আর্দ্রতা" in note for note in result["degraded"])
    blight = next(r for r in result["risks"] if r["key"] == "sheath_blight")
    assert blight["risk_level"] == "high"  # wet-day proxy carried it


def test_treatment_cost_is_withheld_not_estimated(stub_forecast):
    stub_forecast(_days(16, tmax=32.0, tmin=26.0, rh=90.0))
    result = module.pest_risk(crop="aman_rice", district="Dinajpur", sowing_date=_sown(50))

    assert result["treatment_cost_available"] is False
    for risk in result["risks"]:
        assert risk["treatment_cost_bdt"] is None
        assert risk["treatment_cost_note_bn"]


def test_active_risk_carries_a_citation(stub_forecast):
    stub_forecast(_days(16, tmax=32.0, tmin=26.0, rh=90.0))
    result = module.pest_risk(crop="aman_rice", district="Dinajpur", sowing_date=_sown(50))

    for risk in (r for r in result["risks"] if r["status"] == "active"):
        assert risk["source_title"], f"{risk['key']} has no source"
        assert risk["prevention_bn"], f"{risk['key']} has no treatment text"
        assert risk["provenance"]["formula"]


def test_missing_sowing_date_refuses_rather_than_assuming():
    result = module.pest_risk(crop="potato", district="Rangpur")
    assert result["error"] == "sowing_date_required"
    assert result["degraded"] == "তথ্য যথেষ্ট নয়"


def test_unsupported_crop_is_reported_not_guessed():
    result = module.pest_risk(crop="wheat", district="Rangpur", sowing_date=_sown(30))
    assert result["error"] == "unsupported_crop"
    assert "boro_rice" in result["supported"]


def test_every_rule_names_a_real_kb_passage():
    """A rule without a citable passage would be advice we cannot source."""
    corpus = module._corpus_by_id()
    assert corpus, "corpus.json failed to load"
    for crop, rules in module._RULES.items():
        for rule in rules:
            assert rule["kb_id"] in corpus, f"{crop}/{rule['key']} -> {rule['kb_id']}"
