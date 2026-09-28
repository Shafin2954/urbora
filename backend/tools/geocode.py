"""geocode tool — turn a place name into coordinates, with candidate confirmation.

Kill-class risk (NOTES #6): a wrong "Mirpur" silently poisons weather + every
downstream number. Mitigation: return *candidates* and let the agent confirm the
district with the farmer (this doubles as scripted recovery #1). If the live
Open-Meteo geocoder is unreachable, fall back to the hardcoded 64-district table.

All tool params are English (rule 10); farmer-facing confirmation is the agent's
job, in Bangla.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from backend.branding import BRAND_NAME
from .districts import DISTRICTS, lookup_district

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_TIMEOUT = 8.0
_RETRIES = 2


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _fallback(name: str) -> dict:
    """Offline path: match against the 64-district table."""
    hit = lookup_district(name)
    candidates = []
    if hit:
        district, division, lat, lon = hit
        candidates.append(
            {
                "name": district,
                "district": district,
                "division": division,
                "lat": lat,
                "lon": lon,
                "country": "Bangladesh",
            }
        )
    return {
        "query": name,
        "candidates": candidates,
        "source_type": "static_table",
        "source_id": "districts_64",
        "source_title": f"{BRAND_NAME} hardcoded 64-district table",
        "locator": "backend/tools/districts.py",
        "retrieved_at": _now(),
        "cached": True,
        "needs_confirmation": True,
        "note": (
            "Live geocoder unavailable — fell back to district centroids. "
            "Confirm the district with the farmer before using these coordinates."
            if not candidates
            else "District-level fallback; confirm with the farmer."
        ),
    }


def geocode(name: str, count: int = 5) -> dict:
    """Resolve `name` to up to `count` candidate locations in Bangladesh.

    Returns a dict with a `candidates` list ([{name, district, division, lat, lon,
    ...}]) and provenance fields. `needs_confirmation` is always True — the agent
    must confirm the district with the farmer (recovery #1). Degrades to the
    64-district fallback on network failure; never fabricates a location.
    """
    params = {
        "name": name,
        "count": count,
        "language": "en",
        "format": "json",
        "countryCode": "BD",
    }
    last_err: Exception | None = None
    for attempt in range(_RETRIES + 1):
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.get(_GEOCODE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
            results = data.get("results") or []
            candidates = []
            for r in results:
                if r.get("country_code") and r["country_code"] != "BD":
                    continue
                # admin1 is the division; admin2 is usually the district
                district = r.get("admin2") or r.get("admin1") or r.get("name")
                canon = lookup_district(district or "")
                candidates.append(
                    {
                        "name": r.get("name"),
                        "district": canon[0] if canon else district,
                        "division": (canon[1] if canon else r.get("admin1")),
                        "lat": r.get("latitude"),
                        "lon": r.get("longitude"),
                        "country": r.get("country", "Bangladesh"),
                        "population": r.get("population"),
                    }
                )
            if not candidates:
                # live call worked but returned nothing usable → district fallback
                return _fallback(name)
            return {
                "query": name,
                "candidates": candidates,
                "source_type": "api",
                "source_id": "open-meteo-geocoding",
                "source_title": "Open-Meteo Geocoding API",
                "locator": _GEOCODE_URL,
                "retrieved_at": _now(),
                "cached": False,
                "needs_confirmation": True,
                "note": "Multiple candidates possible — confirm the district with the farmer.",
            }
        except Exception as e:  # noqa: BLE001 — retry any network/parse failure
            last_err = e
    # all retries failed → offline fallback
    result = _fallback(name)
    result["error"] = f"geocoder unreachable after {_RETRIES + 1} tries: {last_err}"
    return result


if __name__ == "__main__":
    # Offline-safe: exercise the fallback table without a network call.
    print("districts loaded:", len(DISTRICTS))
    for q in ("Rajshahi", "Bogra", "Jessore", "nowhere-village"):
        r = _fallback(q)
        c = r["candidates"]
        print(f"  {q!r:18} -> {c[0]['district'] if c else 'NO MATCH'}")
