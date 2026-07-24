"""Offline tests for the 64-district table + geocode fallback (NOTES #6).

No network: exercises only the hardcoded table and geocode._fallback.
Run from repo root: `backend/.venv/Scripts/python -m pytest backend/tests -q`
"""

from backend.tools.districts import ALIASES, DISTRICTS, lookup_district
from backend.tools.geocode import _fallback


def test_exactly_64_districts():
    assert len(DISTRICTS) == 64


def test_rajshahi_demo_district_present():
    division, lat, lon = DISTRICTS["Rajshahi"]
    assert division == "Rajshahi"
    assert 24.0 < lat < 25.0 and 88.0 < lon < 89.0


def test_all_coords_within_bangladesh_bbox():
    for name, (_div, lat, lon) in DISTRICTS.items():
        assert 20.5 <= lat <= 26.7, f"{name} lat out of range"
        assert 88.0 <= lon <= 92.7, f"{name} lon out of range"


def test_aliases_resolve_to_canonical():
    cases = {
        "Bogra": "Bogura",
        "Jessore": "Jashore",
        "Comilla": "Cumilla",
        "Chittagong": "Chattogram",
        "Barisal": "Barishal",
    }
    for old, canon in cases.items():
        hit = lookup_district(old)
        assert hit is not None and hit[0] == canon, f"{old} -> {hit}"


def test_alias_keys_point_to_real_districts():
    for target in ALIASES.values():
        assert target in DISTRICTS


def test_loose_match_handles_sadar_suffix():
    hit = lookup_district("Rajshahi Sadar")
    assert hit is not None and hit[0] == "Rajshahi"


def test_unknown_place_returns_none():
    assert lookup_district("Atlantis") is None


def test_fallback_marks_static_table_and_needs_confirmation():
    r = _fallback("Rajshahi")
    assert r["source_type"] == "static_table"
    assert r["cached"] is True
    assert r["needs_confirmation"] is True
    assert r["candidates"] and r["candidates"][0]["district"] == "Rajshahi"


def test_fallback_no_match_returns_empty_candidates_not_fabricated():
    r = _fallback("nowhere-village-xyz")
    assert r["candidates"] == []  # never fabricate a location
