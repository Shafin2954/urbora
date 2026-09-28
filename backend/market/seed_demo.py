"""Seed clearly-labelled DEMO dealers and buyers for the pilot district.

Run once:  python -m backend.market.seed_demo   (idempotent; --reset removes demo rows)

What is real and what is not (CLAUDE.md rule 16):
- Every row here has is_demo=1 and a name that says ডেমো; the UI, SMS and
  agent narration all label them. The phone numbers are made up; a live SMS
  gateway never texts them (backend/market/inputs.py::_send_to_number).
- Fertiliser prices are the government-notified retail prices cited in
  data/prices.md (Urea/TSP ৳27/kg, MoP ৳20/kg; Daily Star notice, 2023-04-11),
  per 50 kg bag. Real dealers may charge differently.
- Pesticide/fungicide prices are INVENTED demo values: no citable source
  exists (README real-vs-mock table). They are labelled "demo" in
  price_source and marked [DEMO] in every listing's provenance.
"""

from __future__ import annotations

import sys

from . import db
from .inputs import register_dealer, upsert_product
from .produce import register_buyer

GOV_NOTICE = "Govt fertiliser price notice via The Daily Star, 2023-04-11 (data/prices.md)"
DEMO_PRICE = "demo value — not a real quote"

DEALERS = [
    ("demo-d1", "ডেমো সার ঘর ১", "Rajshahi", "পবা", "01300000011", True, 1.0),
    ("demo-d2", "ডেমো কৃষি ভান্ডার ২", "Rajshahi", "গোদাগাড়ী", "01300000012", True, 1.08),
    ("demo-d3", "ডেমো কৃষি সেবা ৩", "Natore", "সদর", "01300000013", False, 0.95),
    ("demo-d4", "ডেমো ফসল ঘর ৪", "Naogaon", "সদর", "01300000014", True, 1.03),
    ("demo-d5", "ডেমো বীজ ও সার ৫", "Chapainawabganj", "সদর", "01300000015", False, 0.97),
]
BUYERS = [
    ("demo-b1", "ডেমো পাইকার ১", "wholesaler", "Rajshahi", "01300000021", True),
    ("demo-b2", "ডেমো মজুতদার ২", "stockist", "Bogura", "01300000022", True),
    ("demo-b3", "ডেমো প্রক্রিয়াজাতকারী ৩", "processor", "Natore", "01300000023", False),
]
# (generic, brand, pack_size, unit, base price per pack, cited?)
PRODUCTS = [
    ("urea", "ইউরিয়া (সরকারি)", 50, "kg", 1350, True),
    ("tsp", "টিএসপি (সরকারি)", 50, "kg", 1350, True),
    ("mop", "এমওপি (সরকারি)", 50, "kg", 1000, True),
    ("mancozeb", "ম্যানকোজেব 80 WP", 1, "kg", 620, False),
    ("tricyclazole", "ট্রাইসাইক্লাজল 75 WP", 0.1, "kg", 210, False),
    ("carbendazim", "কার্বেন্ডাজিম 50 WP", 0.5, "kg", 380, False),
]


def reset() -> None:
    for table in ("orders", "products", "dealers", "offers", "produce_listings", "buyers"):
        db.execute(f"DELETE FROM {table} WHERE is_demo = 1" if table != "offers"
                   else "DELETE FROM offers WHERE buyer_id LIKE 'demo-%'")


def seed() -> dict:
    added = {"dealers": 0, "products": 0, "buyers": 0}
    for did, name, district, upazila, phone, verified, factor in DEALERS:
        if not db.row("SELECT 1 FROM dealers WHERE dealer_id = ?", (did,)):
            register_dealer(name, district, phone, upazila, is_demo=True, verified=verified, dealer_id=did)
            added["dealers"] += 1
        for generic, brand, size, unit, price, cited in PRODUCTS:
            pid = f"{did}-{generic}"
            if db.row("SELECT 1 FROM products WHERE product_id = ?", (pid,)):
                continue
            # Cited fertiliser stays at the notified price; demo sprays vary by dealer.
            pack_price = price if cited else round(price * factor)
            upsert_product(did, generic, brand, size, unit, pack_price, 40 if cited else 25,
                           price_source=GOV_NOTICE if cited else DEMO_PRICE, product_id=pid, is_demo=True)
            added["products"] += 1
    for bid, name, kind, district, phone, verified in BUYERS:
        if not db.row("SELECT 1 FROM buyers WHERE buyer_id = ?", (bid,)):
            register_buyer(name, kind, district, phone, is_demo=True, verified=verified, buyer_id=bid)
            added["buyers"] += 1
    return added


if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset()
        print("demo rows removed")
    else:
        print("seeded:", seed())
