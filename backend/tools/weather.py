"""Weather grounding — two clearly-labeled tools (NOTES #1, PRD §6 Tier0.2).

  get_forecast     — Open-Meteo 16-day forecast. source_type="forecast". Actionable.
  get_climatology  — historical normals from the Open-Meteo archive. source_type=
                     "climatology". A PLANNING ASSUMPTION, never a prediction.

A season is 90–120 days; a forecast is 16. Faking month-3 weather is how you lose
the accuracy points, so the two are separate tools with separate source_type
labels and the agent must word them differently in Bangla ("পূর্বাভাস অনুযায়ী"
vs "গত বছরের গড় অনুযায়ী, ভিন্ন হতে পারে"). No invented weather, ever.

Each tool: retry the live call, and on failure fall back to a disk cache of the
last good response, LABELED cached=True (this is also recovery #3). If there is no
cache either, degrade honestly with an `error` field — never fabricate numbers.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
_DAILY_VARS = "temperature_2m_max,temperature_2m_min,precipitation_sum"
_TIMEOUT = 12.0
_RETRIES = 2

_CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "weather"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cache_path(key: str) -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / f"{key}.json"


def _cache_write(key: str, payload: dict) -> None:
    try:
        _cache_path(key).write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass  # cache is best-effort; never fail the tool over it


def _cache_read(key: str) -> dict | None:
    try:
        return json.loads(_cache_path(key).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _get_json(url: str, params: dict) -> dict:
    last_err: Exception | None = None
    for _ in range(_RETRIES + 1):
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise RuntimeError(f"{url} unreachable after {_RETRIES + 1} tries: {last_err}")


# ─────────────────────────────────────────────────────────────────────────────
# Forecast (actionable, 16 days)
# ─────────────────────────────────────────────────────────────────────────────
def get_forecast(lat: float, lon: float, days: int = 16) -> dict:
    """16-day daily forecast for (lat, lon). source_type="forecast".

    Returns {daily:[{date, tmax_c, tmin_c, precip_mm}], source_type, cached, ...}.
    On network failure returns the last cached response labeled cached=True, or an
    `error`/degraded result if no cache exists.
    """
    days = max(1, min(days, 16))
    key = f"forecast_{round(lat, 2)}_{round(lon, 2)}_{days}"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": _DAILY_VARS,
        "forecast_days": days,
        "timezone": "auto",
    }
    base = {
        "source_type": "forecast",
        "source_id": "open-meteo-forecast",
        "source_title": "Open-Meteo 16-day forecast",
        "locator": _FORECAST_URL,
    }
    try:
        data = _get_json(_FORECAST_URL, params)
        d = data.get("daily", {})
        daily = [
            {
                "date": date,
                "tmax_c": tmax,
                "tmin_c": tmin,
                "precip_mm": precip,
            }
            for date, tmax, tmin, precip in zip(
                d.get("time", []),
                d.get("temperature_2m_max", []),
                d.get("temperature_2m_min", []),
                d.get("precipitation_sum", []),
            )
        ]
        result = {**base, "lat": lat, "lon": lon, "daily": daily,
                  "retrieved_at": _now(), "cached": False}
        _cache_write(key, result)
        return result
    except RuntimeError as e:
        cached = _cache_read(key)
        if cached is not None:
            cached["cached"] = True
            cached["stale_note"] = "Live forecast unavailable — showing last cached data."
            return cached
        return {
            **base, "lat": lat, "lon": lon, "daily": [],
            "retrieved_at": _now(), "cached": True,
            "error": str(e),
            "degraded": "তথ্য যথেষ্ট নয়",  # honest degradation, farmer-facing
        }


# ─────────────────────────────────────────────────────────────────────────────
# Climatology (planning assumption — normals from the archive)
# ─────────────────────────────────────────────────────────────────────────────
def get_climatology(lat: float, lon: float, month: int | None = None,
                    years: int = 10) -> dict:
    """Historical monthly normals for (lat, lon). source_type="climatology".

    Averages the past `years` of daily archive data into per-month normals:
    mean daily tmax/tmin (°C) and mean monthly precipitation total (mm). If
    `month` (1–12) is given, only that month's normals are returned. This is a
    planning assumption for months the forecast can't reach — the agent MUST word
    it as an average that may differ, never as a prediction.
    """
    key = f"climo_{round(lat, 2)}_{round(lon, 2)}_{years}"
    # archive lags ~5 days; use whole years ending last completed year.
    end_year = datetime.now(timezone.utc).year - 1
    start = f"{end_year - years + 1}-01-01"
    end = f"{end_year}-12-31"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": _DAILY_VARS,
        "timezone": "auto",
    }
    base = {
        "source_type": "climatology",
        "source_id": "open-meteo-archive",
        "source_title": f"Open-Meteo archive normals ({start[:4]}–{end[:4]})",
        "locator": _ARCHIVE_URL,
        "window": f"{start[:4]}–{end[:4]}",
    }

    def _select(normals: list[dict]) -> list[dict]:
        return [n for n in normals if n["month"] == month] if month else normals

    try:
        data = _get_json(_ARCHIVE_URL, params)
        d = data.get("daily", {})
        times = d.get("time", [])
        tmax = d.get("temperature_2m_max", [])
        tmin = d.get("temperature_2m_min", [])
        precip = d.get("precipitation_sum", [])

        tmax_by_m: dict[int, list[float]] = defaultdict(list)
        tmin_by_m: dict[int, list[float]] = defaultdict(list)
        precip_by_ym: dict[tuple[int, int], float] = defaultdict(float)
        for t, xa, xi, p in zip(times, tmax, tmin, precip):
            y, m, _ = t.split("-")
            y, m = int(y), int(m)
            if xa is not None:
                tmax_by_m[m].append(xa)
            if xi is not None:
                tmin_by_m[m].append(xi)
            if p is not None:
                precip_by_ym[(y, m)] += p

        precip_by_m: dict[int, list[float]] = defaultdict(list)
        for (y, m), total in precip_by_ym.items():
            precip_by_m[m].append(total)

        def _avg(xs: list[float]) -> float | None:
            return round(sum(xs) / len(xs), 1) if xs else None

        normals = [
            {
                "month": m,
                "tmax_c_avg": _avg(tmax_by_m.get(m, [])),
                "tmin_c_avg": _avg(tmin_by_m.get(m, [])),
                "precip_mm_avg": _avg(precip_by_m.get(m, [])),
            }
            for m in range(1, 13)
        ]
        result = {**base, "lat": lat, "lon": lon,
                  "normals": _select(normals), "retrieved_at": _now(), "cached": False}
        # cache the full 12-month set regardless of the month filter
        _cache_write(key, {**base, "lat": lat, "lon": lon, "normals": normals,
                           "retrieved_at": _now(), "cached": False})
        return result
    except RuntimeError as e:
        cached = _cache_read(key)
        if cached is not None:
            cached = dict(cached)
            cached["normals"] = _select(cached.get("normals", []))
            cached["cached"] = True
            cached["stale_note"] = "Live archive unavailable — showing last cached normals."
            return cached
        return {
            **base, "lat": lat, "lon": lon, "normals": [],
            "retrieved_at": _now(), "cached": True,
            "error": str(e),
            "degraded": "তথ্য যথেষ্ট নয়",
        }


if __name__ == "__main__":
    # Live smoke (Rajshahi). Skips gracefully offline.
    la, lo = 24.37, 88.60
    f = get_forecast(la, lo, days=3)
    print("forecast cached:", f.get("cached"), "days:", len(f.get("daily", [])))
    c = get_climatology(la, lo, month=7, years=5)
    print("climatology cached:", c.get("cached"), "normals:", c.get("normals"))
