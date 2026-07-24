"""holt.py — in-event generation of damped-Holt yield projections.

Reads district yield observations from the pre-existing, validated
`agribase_clean.db` (via its safe `recommendation_yields` view — NEVER modifies
it) and writes fresh damped-Holt projections into `data/crop.db` with a `meta`
table carrying generation timestamps + git sha (PRD §5 / §10: derived artifacts
generated in-event with meta timestamps).

Honesty (NOTES #23): with only a handful of points per series, the projection is
a point estimate + a residual band, and `n_points` is always disclosed so the
scorer/UI can say "projection from few years, not a guarantee." Series too short
for Holt fall back to last-observed with a `method` flag — never silently faked.

Units: kg/ha throughout (rule 11 — internal unit is kg). This deviates from PRD
§5's t/ha column naming on purpose, to match the source units and the finance
engine; documented in LOG1.

Run (repo root):  backend/.venv/Scripts/python -m backend.kb.holt
"""

from __future__ import annotations

import sqlite3
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_AGRIBASE = _REPO_ROOT / "agribase_clean.db"
_CROPDB = _REPO_ROOT / "data" / "crop.db"

# Fixed, deterministic smoothing params (no optimizer → reproducible in-event).
_ALPHA, _BETA, _PHI = 0.5, 0.3, 0.9
_MIN_HOLT_POINTS = 4          # below this, fall back to last-observed
_TREND_REL_EPS = 0.01         # |slope/level| under this → "flat"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=_REPO_ROOT, text=True
        ).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _harvest_year(split_year: str) -> int:
    """'2016-17' -> 2017 (end of the split year = harvest year)."""
    a, b = split_year.split("-")
    return int(a[:2] + b) if len(b) == 2 else int(b)


def _classify_trend(slope: float, level: float) -> str:
    if level == 0:
        return "flat"
    rel = slope / level
    if rel > _TREND_REL_EPS:
        return "up"
    if rel < -_TREND_REL_EPS:
        return "down"
    return "flat"


def fit_series(ys: list[float]) -> dict:
    """Fit a series (ordered oldest→newest) → base yield, band, trend, method.

    * n >= 4 : damped Holt, base = 1-step-ahead forecast, band = stdev of in-sample
               one-step residuals, trend from the final damped slope.
    * 2 <= n < 4 : last-observed base, band = sample stdev, trend from overall slope.
    * n == 1 : base = the one value, band = 10% default, trend flat.
    """
    n = len(ys)
    if n == 1:
        return {"base": ys[0], "band": round(0.10 * ys[0], 2),
                "trend": "flat", "method": "single_point", "n": 1}

    if n < _MIN_HOLT_POINTS:
        slope = (ys[-1] - ys[0]) / (n - 1)
        band = statistics.pstdev(ys) if n >= 2 else 0.10 * ys[-1]
        return {"base": round(ys[-1], 2), "band": round(band, 2),
                "trend": _classify_trend(slope, ys[-1]), "method": "last_observed", "n": n}

    # damped Holt
    level = ys[0]
    trend = ys[1] - ys[0]
    resid: list[float] = []
    for t in range(1, n):
        forecast = level + _PHI * trend
        resid.append(ys[t] - forecast)
        new_level = _ALPHA * ys[t] + (1 - _ALPHA) * (level + _PHI * trend)
        trend = _BETA * (new_level - level) + (1 - _BETA) * _PHI * trend
        level = new_level
    base = level + _PHI * trend
    band = statistics.pstdev(resid) if len(resid) >= 2 else 0.10 * level
    return {"base": round(base, 2), "band": round(band, 2),
            "trend": _classify_trend(trend, level), "method": "damped_holt", "n": n}


def build() -> dict:
    """Generate data/crop.db from agribase_clean.db. Returns a small summary."""
    if not _AGRIBASE.exists():
        raise FileNotFoundError(f"source db not found: {_AGRIBASE}")
    _CROPDB.parent.mkdir(parents=True, exist_ok=True)

    src = sqlite3.connect(f"file:{_AGRIBASE}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row

    # pull enabled crops + all accepted observations
    enabled = [
        r["crop_key"]
        for r in src.execute(
            "SELECT crop_key FROM crop_catalog WHERE enabled_for_recommendation=1"
        )
    ]
    series: dict[tuple[str, str], list[tuple[int, float]]] = {}
    display: dict[str, str] = {}
    for r in src.execute(
        "SELECT crop_key, display_name, district, year, yield_kg_per_ha "
        "FROM recommendation_yields"
    ):
        if r["crop_key"] not in enabled or r["yield_kg_per_ha"] is None:
            continue
        display[r["crop_key"]] = r["display_name"]
        series.setdefault((r["crop_key"], r["district"]), []).append(
            (_harvest_year(r["year"]), float(r["yield_kg_per_ha"]))
        )
    src.close()

    out = sqlite3.connect(_CROPDB)
    out.execute("DROP TABLE IF EXISTS holt_projections")
    out.execute("DROP TABLE IF EXISTS meta")
    out.execute(
        """
        CREATE TABLE holt_projections (
            crop_key        TEXT NOT NULL,
            display_name    TEXT NOT NULL,
            district        TEXT NOT NULL,
            base_yield_kg_ha REAL NOT NULL,
            band_kg_ha      REAL NOT NULL,
            n_points        INTEGER NOT NULL,
            trend           TEXT NOT NULL,          -- up|flat|down
            method          TEXT NOT NULL,          -- damped_holt|last_observed|single_point
            fitted_at       TEXT NOT NULL,
            PRIMARY KEY (crop_key, district)
        )
        """
    )
    out.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")

    fitted_at = _now()
    per_crop: dict[str, int] = {}
    holt_count = 0
    for (crop, district), pts in series.items():
        pts.sort(key=lambda x: x[0])
        ys = [y for _, y in pts]
        f = fit_series(ys)
        out.execute(
            "INSERT INTO holt_projections VALUES (?,?,?,?,?,?,?,?,?)",
            (crop, display.get(crop, crop), district, f["base"], f["band"],
             f["n"], f["trend"], f["method"], fitted_at),
        )
        per_crop[crop] = per_crop.get(crop, 0) + 1
        if f["method"] == "damped_holt":
            holt_count += 1

    meta = {
        "generated_at": fitted_at,
        "parser_git_sha": _git_sha(),
        "source_db": "agribase_clean.db",
        "source_view": "recommendation_yields",
        "source_registry_status": "pending_verification",
        "holt_params": f"alpha={_ALPHA},beta={_BETA},phi={_PHI},min_points={_MIN_HOLT_POINTS}",
        "enabled_crops": ",".join(sorted(enabled)),
        "unit": "kg_per_ha",
        "disclaimer": "District yield projections from a validated derivative of the "
                      "supplied dataset; in-database source citation pending verification.",
    }
    out.executemany("INSERT INTO meta VALUES (?,?)", list(meta.items()))
    out.commit()
    out.close()

    return {
        "rows": sum(per_crop.values()),
        "per_crop": per_crop,
        "damped_holt_series": holt_count,
        "db": str(_CROPDB),
    }


if __name__ == "__main__":
    summary = build()
    print("crop.db generated:", summary["db"])
    print("  total projection rows:", summary["rows"])
    print("  damped-Holt series   :", summary["damped_holt_series"])
    for crop, n in sorted(summary["per_crop"].items()):
        print(f"    {crop:14} {n} districts")
