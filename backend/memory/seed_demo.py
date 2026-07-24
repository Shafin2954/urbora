"""Seed the rehearsed demo farm (PLAN.md §5 step 1, PRD §15 decision 3).

The demo opens on a returning farmer: the agent greets them and recalls their
farm, which is the Memory behaviour in PRD §4. That needs a profile already in
the store before the first turn — not because the memory is fake, but because a
demo cannot spend its first minute doing intake.

Run from the repo root:

    .venv/Scripts/python -m backend.memory.seed_demo

This writes ONE farm profile. It writes no yields, no prices, and no advice —
everything the agent says about this farm still comes from live tools and cited
data at demo time. What is seeded is only what a farmer would have told us in a
previous conversation.
"""

from __future__ import annotations

import json
import sys

from .store import get_farm, save_farm

DEMO_FARM_ID = "demo-rajshahi"

# Rajshahi because PRD §3.3 fixes it as the demo district: the High Ganges
# Floodplain and the Barind Tract meet there, which is what makes the AEZ soil
# cross-check earn its place. Rabi because that is the season a farmer is
# realistically planning in July — seed booking and input budgeting.
DEMO_FARM = {
    "name": "করিম উদ্দিন",
    "district": "Rajshahi",
    "area": 1,
    "area_unit": "bigha",
    "soil_type": "clay_loam",
    "water_source": "irrigated",
    "budget_bdt": 20000,
    "season": "rabi",
}


def seed(force: bool = False) -> dict:
    existing = get_farm(DEMO_FARM_ID)
    if existing and not force:
        return existing
    save_farm(DEMO_FARM_ID, DEMO_FARM)
    return DEMO_FARM


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001 — Windows cp1252 cannot print Bangla
        pass
    profile = seed(force="--force" in sys.argv)
    print(f"farm_id: {DEMO_FARM_ID}")
    print(json.dumps(profile, ensure_ascii=False, indent=2))
