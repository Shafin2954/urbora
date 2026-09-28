"""Deterministic supplier ranking — the model never ranks dealers (rule 1).

Score out of 100, every component returned so the agent can say why a dealer
is first ("cheapest per kg, 4 km away") without computing anything:

| component | max | rule |
|---|---|---|
| price    | 40 | 40 × cheapest unit price in the set / this unit price |
| distance | 30 | 30 × (1 − km / MAX_KM), floored at 0 |
| stock    | 15 | 15 if it covers the packs needed (or no quantity asked), else pro rata |
| trust    | 15 | verified dealer 10 + completed orders (0.5 each, max 5); unverified: orders only |

Nobody can pay to rank higher: there is no paid term. Ties break on unit
price, then distance, then dealer id, so the same inputs always give the same
order.
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

MAX_KM = 80.0
WEIGHTS = {"price": 40.0, "distance": 30.0, "stock": 15.0, "trust": 15.0}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


def score_offers(offers: list[dict], packs_needed: dict[str, int] | None = None) -> list[dict]:
    """offers: dicts with product_id, unit_price, km, stock_packs, verified,
    completed_orders, dealer_id. Returns new dicts with `score`,
    `components` and `rank`, best first. Offers beyond MAX_KM are dropped."""
    near = [o for o in offers if o["km"] <= MAX_KM]
    if not near:
        return []
    cheapest = min(o["unit_price"] for o in near)
    out = []
    for o in near:
        need = (packs_needed or {}).get(o["product_id"])
        stock_ratio = 1.0 if not need else min(1.0, o["stock_packs"] / need)
        trust = (10.0 if o["verified"] else 0.0) + min(5.0, 0.5 * o["completed_orders"])
        comps = {
            "price": round(WEIGHTS["price"] * cheapest / o["unit_price"], 2),
            "distance": round(WEIGHTS["distance"] * max(0.0, 1 - o["km"] / MAX_KM), 2),
            "stock": round(WEIGHTS["stock"] * stock_ratio, 2),
            "trust": round(trust, 2),
        }
        out.append({**o, "components": comps, "score": round(sum(comps.values()), 2)})
    out.sort(key=lambda o: (-o["score"], o["unit_price"], o["km"], o["dealer_id"]))
    for i, o in enumerate(out, 1):
        o["rank"] = i
    return out
