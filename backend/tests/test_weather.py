"""Offline tests for weather labeling + degradation + climatology aggregation.

Network is monkeypatched out — we assert the honesty rules (NOTES #1), not live
Open-Meteo data.
"""

import backend.tools.weather as weather


def test_forecast_degrades_honestly_when_offline_and_uncached(monkeypatch):
    def _boom(url, params):
        raise RuntimeError("network down")

    monkeypatch.setattr(weather, "_get_json", _boom)
    # coords unlikely to have a cache file
    r = weather.get_forecast(1.23, 4.56, days=3)
    assert r["source_type"] == "forecast"
    assert r["cached"] is True
    assert r["daily"] == []
    assert r["degraded"] == "তথ্য যথেষ্ট নয়"  # honest, not fabricated
    assert "error" in r


def test_forecast_labels_source_type_forecast(monkeypatch):
    fake = {
        "daily": {
            "time": ["2026-07-24", "2026-07-25"],
            "temperature_2m_max": [33.1, 32.5],
            "temperature_2m_min": [26.0, 25.8],
            "precipitation_sum": [12.0, 0.0],
        }
    }
    monkeypatch.setattr(weather, "_get_json", lambda url, params: fake)
    r = weather.get_forecast(24.37, 88.60, days=2)
    assert r["source_type"] == "forecast"
    assert r["cached"] is False
    assert len(r["daily"]) == 2
    # humidity_pct is None, not absent and not 0: this fake response carries no
    # relative_humidity_2m_mean, and pest_risk must be able to tell "dry air"
    # from "we were not told".
    assert r["daily"][0] == {"date": "2026-07-24", "tmax_c": 33.1,
                             "tmin_c": 26.0, "precip_mm": 12.0,
                             "humidity_pct": None}


def test_climatology_labels_and_aggregates(monkeypatch):
    # two years of July data → precip normal = mean of the two yearly sums.
    fake = {
        "daily": {
            "time": ["2018-07-01", "2018-07-02", "2019-07-01", "2019-07-02"],
            "temperature_2m_max": [34.0, 36.0, 30.0, 32.0],
            "temperature_2m_min": [26.0, 26.0, 24.0, 24.0],
            "precipitation_sum": [10.0, 10.0, 30.0, 30.0],  # 2018 sum=20, 2019 sum=60
        }
    }
    monkeypatch.setattr(weather, "_get_json", lambda url, params: fake)
    r = weather.get_climatology(24.37, 88.60, month=7, years=2)
    assert r["source_type"] == "climatology"
    assert r["cached"] is False
    assert len(r["normals"]) == 1
    july = r["normals"][0]
    assert july["month"] == 7
    assert july["tmax_c_avg"] == 33.0            # mean(34,36,30,32)
    assert july["precip_mm_avg"] == 40.0         # mean(20, 60)


def test_climatology_degrades_when_offline_and_uncached(monkeypatch):
    def _boom(url, params):
        raise RuntimeError("archive down")

    monkeypatch.setattr(weather, "_get_json", _boom)
    r = weather.get_climatology(1.23, 4.56, month=3, years=2)
    assert r["source_type"] == "climatology"
    assert r["normals"] == []
    assert r["degraded"] == "তথ্য যথেষ্ট নয়"
