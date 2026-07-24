"""Tests for the cropdb_sql tool against the real dbs (read-only).

crop.db is a generated in-event artifact; regenerate it if absent so the suite is
self-contained.
"""

import pytest

from backend.kb import holt
from backend.tools import cropdb


@pytest.fixture(scope="module", autouse=True)
def ensure_cropdb():
    if not cropdb._CROPDB.exists():
        holt.build()


def test_resolve_crop_maps_canonical_and_keys():
    assert cropdb.resolve_crop("boro_rice") == "boro_hyv"
    assert cropdb.resolve_crop("aman_hyv") == "aman_hyv"
    assert cropdb.resolve_crop("potato") == "potato_hyv"
    assert cropdb.resolve_crop("wheat") is None  # no data → not resolvable
    assert cropdb.resolve_crop("maize") is None


def test_district_yields_has_observations_and_dataset_provenance():
    r = cropdb.cropdb_sql("district_yields", "boro_rice", "Rajshahi")
    assert "error" not in r
    assert r["source_type"] == "dataset"
    assert r["confidence"] == "medium"  # pending_verification
    assert r["observations"] and all("yield_kg_ha" in o for o in r["observations"])


def test_holt_projection_shape_and_disclosure():
    r = cropdb.cropdb_sql("holt_projection", "boro_rice", "Rajshahi")
    assert "error" not in r
    assert r["source_type"] == "computed"
    assert r["base_yield_kg_ha"] > 0
    assert r["band_kg_ha"] >= 0
    assert r["n_points"] >= 1
    assert r["trend"] in {"up", "flat", "down"}
    assert r["method"] in {"damped_holt", "last_observed", "single_point"}
    assert "not a guarantee" in r["formula"].lower()


def test_yield_track_record_percentile_in_range():
    r = cropdb.cropdb_sql("yield_track_record", "boro_rice", "Rajshahi")
    assert "error" not in r
    assert 0.0 <= r["percentile_vs_districts"] <= 100.0
    assert r["latest_yield_kg_ha"] > 0
    assert r["n_districts"] > 1


def test_wheat_and_maize_return_honest_absence_not_numbers():
    for crop in ("wheat", "maize"):
        r = cropdb.cropdb_sql("holt_projection", crop, "Rajshahi")
        assert "error" in r
        assert "available_crops" in r
        assert crop not in r["available_crops"]


def test_unknown_district_and_action_are_safe():
    assert "error" in cropdb.cropdb_sql("holt_projection", "boro_rice", "Atlantis")
    assert "error" in cropdb.cropdb_sql("nope", "boro_rice", "Rajshahi")
