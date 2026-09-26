"""Produce marketplace: farmers list the harvest, buyers offer, farmers accept.

Why it exists: farmers keep well under half of the consumer price (ADB: 27–45%
for common vegetables), partly because they sell to the first trader at the
farm gate without knowing what a fair price is. So every listing comes with a
**price guide** built only from cited data:

- the farm-gate row from data/prices.md (what farmers were paid, dated), and
- the historical wholesale pattern from `market_price` (BBS; labelled a
  pattern, not a forecast, and wholesale, not farm-gate).

Money: the farmer receives the agreed qty × price in full; the buyer pays the
platform fee on top (backend/finance/market.py::deal_totals). Contacts are
exchanged only after the farmer accepts. Escrow, logistics and quality
disputes are out of scope for the pilot and said so.

Listing states: open → sold | withdrawn. Offer states: pending → accepted |
rejected | withdrawn.
"""

from __future__ import annotations

import json
from datetime import date

from backend.channels.sms_text import CROP_BN
from backend.finance import market as money
from backend.tools.districts import lookup_district

from . import db
from .ranking import haversine_km

CROPS = ("boro_rice", "aman_rice", "potato", "mustard", "lentil")
MAX_BUYER_KM = 150.0


class ProduceError(ValueError):
    pass


def price_guide(crop: str) -> dict:
    """Cited reference prices for a crop. Never a prediction."""
    guide: dict = {"crop": crop}
    try:
        from backend.finance.catalog import load_catalog
        row = load_catalog().price(crop)
        if row:
            guide["farm_gate"] = {
                "price_bdt_per_kg": row.price_bdt_per_kg, "date": row.date, "basis": row.basis,
                "provenance": {"value": row.price_bdt_per_kg, "unit": "BDT/kg", "source_type": "static_table",
                               "source_id": row.source_id, "source_title": row.source_title,
                               "locator": row.locator, "retrieved_at": db.now(), "confidence": row.confidence},
            }
    except Exception:  # noqa: BLE001 — a missing guide is disclosed, not invented
        pass
    try:
        from backend.tools.market_price import market_price
        mp = market_price(crop)
        if not mp.get("error"):
            guide["wholesale_pattern"] = {
                "this_month_avg_bdt_per_kg": mp.get("current_month_avg_bdt_per_kg"),
                "best_later_month": mp.get("best_later_month"),
                "best_later_month_avg_bdt_per_kg": mp.get("best_later_month_avg_bdt_per_kg"),
                "years_covered": mp.get("years_covered"),
                "not_a_forecast": True, "is_farm_gate": False,
                "provenance": mp.get("provenance"),
            }
    except Exception:  # noqa: BLE001
        pass
    if len(guide) == 1:
        guide["note"] = "No cited price for this crop; the guide is unavailable."
    return guide


def guide_sms_line(guide: dict) -> str:
    parts = []
    if "farm_gate" in guide:
        fg = guide["farm_gate"]
        parts.append(f"খামার-দাম ৳{fg['price_bdt_per_kg']:g}/কেজি ({fg['date']})")
    if "wholesale_pattern" in guide and guide["wholesale_pattern"]["this_month_avg_bdt_per_kg"]:
        parts.append(f"পাইকারি গড় এ মাসে ৳{guide['wholesale_pattern']['this_month_avg_bdt_per_kg']:g}/কেজি")
    return "দামের ধারণা: " + "; ".join(parts) if parts else ""


def create_listing(farm_id: str, crop: str, qty_kg: float, asking_price_per_kg: float | None = None,
                   district: str | None = None, available_from: str | None = None,
                   channel: str = "web", *, is_demo: bool = False) -> dict:
    if crop not in CROPS:
        raise ProduceError(f"crop must be one of {', '.join(CROPS)}")
    if not qty_kg or qty_kg <= 0:
        raise ProduceError("quantity must be positive")
    if asking_price_per_kg is not None and asking_price_per_kg <= 0:
        raise ProduceError("asking price must be positive")
    if not district:
        from backend.memory import store
        district = (store.get_farm(farm_id) or {}).get("district")
    hit = lookup_district(district or "")
    if not hit:
        raise ProduceError("district unknown — say which district the crop is in")
    listing_id = db.execute(
        "INSERT INTO produce_listings (farm_id, crop, qty_kg, asking_price_per_kg, district, available_from, "
        "status, channel, is_demo, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (farm_id, crop, float(qty_kg), asking_price_per_kg, hit[0], available_from or date.today().isoformat(),
         "open", channel, int(is_demo), db.now()))
    listing = get_listing(listing_id)
    _notify_buyers(listing)
    return listing


def get_listing(listing_id: int) -> dict:
    lst = db.row("SELECT * FROM produce_listings WHERE listing_id = ?", (listing_id,))
    if not lst:
        raise ProduceError("unknown listing")
    lst["offers"] = [_offer_out(o) for o in db.rows(
        "SELECT * FROM offers WHERE listing_id = ? ORDER BY price_per_kg DESC, offer_id", (listing_id,))]
    lst["price_guide"] = price_guide(lst["crop"])
    return lst


def _offer_out(o: dict) -> dict:
    b = db.row("SELECT name, kind, district, verified, completed_deals, is_demo FROM buyers WHERE buyer_id = ?",
               (o["buyer_id"],)) or {}
    out = {k: o[k] for k in ("offer_id", "listing_id", "buyer_id", "price_per_kg", "qty_kg",
                             "pickup_date", "status", "created_at")}
    out["totals"] = json.loads(o["totals_json"]) if o.get("totals_json") else None
    out["buyer"] = {**b, "is_demo": bool(b.get("is_demo"))}
    return out


def farm_listings(farm_id: str) -> list[dict]:
    return [get_listing(r["listing_id"]) for r in db.rows(
        "SELECT listing_id FROM produce_listings WHERE farm_id = ? ORDER BY listing_id DESC", (farm_id,))]


def open_listings_near(district: str) -> list[dict]:
    here = lookup_district(district or "")
    out = []
    for lst in db.rows("SELECT * FROM produce_listings WHERE status = 'open' ORDER BY listing_id DESC"):
        there = lookup_district(lst["district"])
        km = haversine_km(here[2], here[3], there[2], there[3]) if here and there else None
        if km is None or km <= MAX_BUYER_KM:
            lst["km"] = round(km, 1) if km is not None else None
            lst["offer_count"] = len(db.rows("SELECT 1 FROM offers WHERE listing_id = ?", (lst["listing_id"],)))
            lst["price_guide"] = price_guide(lst["crop"])
            lst.pop("farm_id")  # buyers never see who the farmer is before acceptance
            out.append(lst)
    return out


def make_offer(buyer_id: str, listing_id: int, price_per_kg: float, qty_kg: float | None = None,
               pickup_date: str | None = None) -> dict:
    lst = db.row("SELECT * FROM produce_listings WHERE listing_id = ?", (listing_id,))
    if not lst or lst["status"] != "open":
        raise ProduceError("listing is not open")
    qty = float(qty_kg or lst["qty_kg"])
    if qty > lst["qty_kg"]:
        raise ProduceError("offer quantity exceeds the listing")
    totals = money.deal_totals(qty, price_per_kg)
    ts = db.now()
    offer_id = db.execute(
        "INSERT INTO offers (listing_id, buyer_id, price_per_kg, qty_kg, pickup_date, status, totals_json, "
        "created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (listing_id, buyer_id, float(price_per_kg), qty, pickup_date, "pending", db.dumps(totals), ts, ts))
    offer = _offer_out(db.row("SELECT * FROM offers WHERE offer_id = ?", (offer_id,)))
    _notify_farmer_offer(lst, offer)
    return offer


def respond_to_offer(farm_id: str, offer_id: int, accept: bool) -> dict:
    o = db.row("SELECT * FROM offers WHERE offer_id = ?", (offer_id,))
    if not o:
        raise ProduceError("unknown offer")
    lst = db.row("SELECT * FROM produce_listings WHERE listing_id = ?", (o["listing_id"],))
    if lst["farm_id"] != farm_id:
        raise ProduceError("not your listing")
    if o["status"] != "pending" or lst["status"] != "open":
        raise ProduceError("this offer is no longer open")
    ts = db.now()
    if not accept:
        db.execute("UPDATE offers SET status='rejected', updated_at=? WHERE offer_id=?", (ts, offer_id))
        return _offer_out(db.row("SELECT * FROM offers WHERE offer_id = ?", (offer_id,)))
    db.execute("UPDATE offers SET status='accepted', updated_at=? WHERE offer_id=?", (ts, offer_id))
    db.execute("UPDATE offers SET status='rejected', updated_at=? WHERE listing_id=? AND offer_id<>? "
               "AND status='pending'", (ts, o["listing_id"], offer_id))
    db.execute("UPDATE produce_listings SET status='sold' WHERE listing_id=?", (o["listing_id"],))
    db.execute("UPDATE buyers SET completed_deals = completed_deals + 1 WHERE buyer_id=?", (o["buyer_id"],))
    offer = _offer_out(db.row("SELECT * FROM offers WHERE offer_id = ?", (offer_id,)))
    _exchange_contacts(lst, offer)
    return offer


def register_buyer(name: str, kind: str, district: str, msisdn: str, *, is_demo: bool = False,
                   verified: bool = False, buyer_id: str | None = None) -> dict:
    from backend.channels.identity import normalise
    if kind not in ("wholesaler", "stockist", "processor", "retailer"):
        raise ProduceError("kind must be wholesaler, stockist, processor or retailer")
    hit = lookup_district(district or "")
    if not hit:
        raise ProduceError(f"unknown district '{district}'")
    buyer_id = buyer_id or f"b-{db.new_token()[:8]}"
    token = db.new_token()
    db.execute(
        "INSERT INTO buyers (buyer_id, name, kind, district, msisdn, verified, token, is_demo, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (buyer_id, name.strip(), kind, hit[0], normalise(msisdn), int(verified), token, int(is_demo), db.now()))
    return {"buyer_id": buyer_id, "token": token}


def buyer_by_token(token: str) -> dict:
    b = db.row("SELECT * FROM buyers WHERE token = ?", (token or "",))
    if not b:
        raise ProduceError("unknown buyer token")
    return b


def buyer_view(buyer: dict) -> dict:
    return {
        "buyer": {k: buyer[k] for k in ("buyer_id", "name", "kind", "district", "verified",
                                         "completed_deals", "is_demo")},
        "listings": open_listings_near(buyer["district"]),
        "offers": [_offer_out(o) for o in db.rows(
            "SELECT * FROM offers WHERE buyer_id = ? ORDER BY offer_id DESC LIMIT 50", (buyer["buyer_id"],))],
    }


# --- SMS -------------------------------------------------------------------------


def _notify_buyers(listing: dict) -> None:
    from .inputs import _send_to_number
    ask = f", চাওয়া দাম ৳{listing['asking_price_per_kg']:g}/কেজি" if listing["asking_price_per_kg"] else ""
    for b in db.rows("SELECT * FROM buyers"):
        here, there = lookup_district(b["district"]), lookup_district(listing["district"])
        if here and there and haversine_km(here[2], here[3], there[2], there[3]) <= MAX_BUYER_KM:
            _send_to_number(b["msisdn"], demo=bool(b["is_demo"]), text=(
                f"নতুন ফসল #{listing['listing_id']}: {CROP_BN.get(listing['crop'], listing['crop'])} "
                f"{listing['qty_kg']:g} কেজি, {listing['district']}{ask}। অফার দিন ক্রেতা পাতায়।"))


def _notify_farmer_offer(listing: dict, offer: dict) -> None:
    from backend.channels import sms
    b = offer["buyer"]
    demo = " (ডেমো ক্রেতা)" if b.get("is_demo") else ""
    t = offer["totals"]
    sms.send_sms(listing["farm_id"], (
        f"অফার #{offer['offer_id']}: {b.get('name', '')}{demo}\n"
        f"{CROP_BN.get(listing['crop'], listing['crop'])} {offer['qty_kg']:g} কেজি × ৳{offer['price_per_kg']:g} "
        f"= আপনি পাবেন ৳{t['farmer_receives']:,.0f}\n"
        f"গ্রহণ: গ্রহণ {offer['offer_id']}  বাতিল: বাতিল {offer['offer_id']}"
    ))


def _exchange_contacts(listing: dict, offer: dict) -> None:
    from backend.channels import sms
    from backend.memory import store

    from .inputs import _send_to_number
    buyer = db.row("SELECT * FROM buyers WHERE buyer_id = ?", (offer["buyer_id"],))
    farmer = store.get_contact(listing["farm_id"]) or {}
    t = offer["totals"]
    sms.send_sms(listing["farm_id"], (
        f"চুক্তি হয়েছে #{offer['offer_id']}। ক্রেতা: {buyer['name']}, ফোন {buyer['msisdn']}"
        f"{' (ডেমো ক্রেতা, আসল নম্বর নয়)' if buyer['is_demo'] else ''}। "
        f"আপনি পাবেন ৳{t['farmer_receives']:,.0f}।"
    ))
    if farmer.get("msisdn"):
        _send_to_number(buyer["msisdn"], demo=bool(buyer["is_demo"]), text=(
            f"চুক্তি #{offer['offer_id']} গৃহীত: {CROP_BN.get(listing['crop'], listing['crop'])} "
            f"{offer['qty_kg']:g} কেজি, {listing['district']}। কৃষকের ফোন {farmer['msisdn']}। "
            f"মোট ৳{t['buyer_pays']:,.0f} (ফি ৳{t['platform_fee']:,.0f} সহ)।"
        ))
