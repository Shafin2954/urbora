"""cropdb_sql tool — read-only district yield facts with provenance.

Backed by the validated `agribase_clean.db` (safe views only) for observed yields
and by the in-event `data/crop.db` for damped-Holt projections. This is the agent's
window onto yield NUMBERS during conversation/trace; the deterministic crop_scorer
(later block) reads the same data directly in Python.

Safety: NOT a raw-SQL surface for the LLM. The tool exposes a fixed set of
parameterized actions (district_yields / holt_projection / yield_track_record) —
the model passes crop + district, never SQL. Read-only DB connections.

Every returned number carries the fields needed to build a Provenance:
observed yields → source_type=dataset (confidence medium: source_registry is
pending_verification); Holt → source_type=computed with a formula naming n_points.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from backend.branding import BRAND_NAME
from .districts import lookup_district

_REPO_ROOT = Path(__file__).resolve().parents[2]
_AGRIBASE = _REPO_ROOT / "agribase_clean.db"
_CROPDB = _REPO_ROOT / "data" / "crop.db"

# canonical crop name (what KB / scorer use) -> agribase_clean.db crop_key.
# NOTE: wheat + maize from PRD §3.2 have NO yield data in this db (wheat disabled,
# maize absent) — they are intentionally NOT rankable from data (PRD §5 rule 3).
CANON_TO_KEY: dict[str, str] = {
    "boro_rice": "boro_hyv",
    "aman_rice": "aman_hyv",
    "potato": "potato_hyv",
    "mustard": "mustard",
    "lentil": "lentil_masur",
}
_KEY_TO_CANON = {v: k for k, v in CANON_TO_KEY.items()}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def resolve_crop(name: str) -> str | None:
    """Accept a canonical name, a db crop_key, or a loose display match → db key."""
    key = name.strip().lower().replace(" ", "_")
    if key in CANON_TO_KEY:
        return CANON_TO_KEY[key]
    if key in _KEY_TO_CANON:
        return key
    for canon, dbkey in CANON_TO_KEY.items():
        if canon.startswith(key) or key in canon:
            return dbkey
    if "rice" in key and "boro" in key:
        return "boro_hyv"
    if "rice" in key and "aman" in key:
        return "aman_hyv"
    return None


def _canon_district(name: str) -> str | None:
    hit = lookup_district(name)
    return hit[0] if hit else None


_DATASET_PROV = {
    "source_type": "dataset",
    "source_id": "agribase_clean",
    "source_title": "Validated derivative of supplied district yield dataset",
    "locator": "agribase_clean.db :: recommendation_yields",
    "confidence": "medium",  # source_registry pending_verification
    "note": "In-database source citation pending verification (not BBS-verified).",
}


def _crop_absent(name: str) -> dict:
    return {
        "error": f"no yield data for crop '{name}'",
        "available_crops": sorted(CANON_TO_KEY),
        "note": "Wheat and maize have no yield series in this dataset and cannot "
                "be ranked from data — say so honestly rather than estimating.",
    }


def district_yields(crop: str, district: str) -> dict:
    """Observed district yield history (kg/ha) for crop×district."""
    dbkey = resolve_crop(crop)
    if dbkey is None:
        return _crop_absent(crop)
    canon_dist = _canon_district(district)
    if canon_dist is None:
        return {"error": f"unknown district '{district}'"}
    conn = _ro(_AGRIBASE)
    rows = conn.execute(
        "SELECT year, yield_kg_per_ha, hectares, production_mt "
        "FROM recommendation_yields WHERE crop_key=? AND district=? ORDER BY year",
        (dbkey, canon_dist),
    ).fetchall()
    conn.close()
    return {
        "crop": _KEY_TO_CANON.get(dbkey, dbkey),
        "district": canon_dist,
        "observations": [
            {"year": r["year"], "yield_kg_ha": round(r["yield_kg_per_ha"], 1),
             "hectares": r["hectares"], "production_mt": r["production_mt"]}
            for r in rows
        ],
        "retrieved_at": _now(),
        **_DATASET_PROV,
    }


def holt_projection(crop: str, district: str) -> dict:
    """Damped-Holt base yield + band for crop×district (source_type=computed)."""
    dbkey = resolve_crop(crop)
    if dbkey is None:
        return _crop_absent(crop)
    canon_dist = _canon_district(district)
    if canon_dist is None:
        return {"error": f"unknown district '{district}'"}
    if not _CROPDB.exists():
        return {"error": "crop.db not generated — run `python -m backend.kb.holt`"}
    conn = _ro(_CROPDB)
    r = conn.execute(
        "SELECT base_yield_kg_ha, band_kg_ha, n_points, trend, method, fitted_at "
        "FROM holt_projections WHERE crop_key=? AND district=?",
        (dbkey, canon_dist),
    ).fetchone()
    conn.close()
    if r is None:
        return {"error": f"no projection for {crop} in {canon_dist}"}
    conf = "medium" if r["method"] == "damped_holt" and r["n_points"] >= 6 else "low"
    return {
        "crop": _KEY_TO_CANON.get(dbkey, dbkey),
        "district": canon_dist,
        "base_yield_kg_ha": r["base_yield_kg_ha"],
        "band_kg_ha": r["band_kg_ha"],
        "n_points": r["n_points"],
        "trend": r["trend"],
        "method": r["method"],
        "source_type": "computed",
        "source_id": "crop.db/holt_projections",
        "source_title": f"{BRAND_NAME} damped-Holt projection (in-event)",
        "formula": f"{r['method']} over {canon_dist} {crop}, n={r['n_points']} years; "
                   f"base ± band (residual sd). Projection, not a guarantee.",
        "confidence": conf,
        "fitted_at": r["fitted_at"],
        "retrieved_at": _now(),
    }


def yield_track_record(crop: str, district: str) -> dict:
    """District's latest yield vs same crop across all districts → percentile
    (feeds the scorer's 'district track record' component; also surfaceable)."""
    dbkey = resolve_crop(crop)
    if dbkey is None:
        return _crop_absent(crop)
    canon_dist = _canon_district(district)
    if canon_dist is None:
        return {"error": f"unknown district '{district}'"}
    conn = _ro(_AGRIBASE)
    rows = conn.execute(
        "SELECT district, yield_kg_per_ha FROM latest_district_yields WHERE crop_key=?",
        (dbkey,),
    ).fetchall()
    conn.close()
    vals = {r["district"]: r["yield_kg_per_ha"] for r in rows if r["yield_kg_per_ha"]}
    if canon_dist not in vals:
        return {"error": f"no latest yield for {crop} in {canon_dist}",
                "n_districts": len(vals)}
    target = vals[canon_dist]
    below = sum(1 for v in vals.values() if v < target)
    pct = round(100.0 * below / (len(vals) - 1), 1) if len(vals) > 1 else 100.0
    return {
        "crop": _KEY_TO_CANON.get(dbkey, dbkey),
        "district": canon_dist,
        "latest_yield_kg_ha": round(target, 1),
        "percentile_vs_districts": pct,
        "n_districts": len(vals),
        "source_type": "dataset",
        "source_id": "agribase_clean",
        "source_title": "Validated derivative of supplied district yield dataset",
        "locator": "agribase_clean.db :: latest_district_yields",
        "confidence": "medium",
        "retrieved_at": _now(),
    }


_ACTIONS = {
    "district_yields": district_yields,
    "holt_projection": holt_projection,
    "yield_track_record": yield_track_record,
}


def cropdb_sql(action: str, crop: str, district: str) -> dict:
    """Entrypoint for the cropdb_sql tool. `action` selects a parameterized query."""
    fn = _ACTIONS.get(action)
    if fn is None:
        return {"error": f"unknown action '{action}'", "actions": sorted(_ACTIONS)}
    return fn(crop=crop, district=district)


if __name__ == "__main__":
    for act in _ACTIONS:
        print(f"--- {act}: boro_rice / Rajshahi ---")
        r = cropdb_sql(act, "boro_rice", "Rajshahi")
        print("  ", {k: r[k] for k in list(r)[:6]})
    print("--- wheat (should be absent) ---")
    print("  ", cropdb_sql("holt_projection", "wheat", "Rajshahi"))
