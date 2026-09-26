"""Input marketplace: find offers (agent tool), place orders, dealer actions.

Flow, on any channel:
1. The agent recommends an input (a dose from the KB, a spray from pest_risk)
   and calls `find_inputs` — ranked nearby offers, each price carrying
   provenance `source_type: listing` that names the dealer and the date.
2. The farmer orders (web button, USSD menu, or SMS reply). `place_order`
   prices it in backend/finance/market.py and texts the dealer.
3. The dealer confirms by SMS ("হ্যাঁ 12") or on the dealer page; the farmer is
   texted at each step. Payment is cash on collection by default; phone-balance
   payment reuses the bdapps checkout.

Order states: placed → confirmed → ready → collected | delivered;
placed/confirmed → cancelled. Anything else is refused.
"""

from __future__ import annotations

import json

from backend.finance import market as money
from backend.tools.districts import lookup_district

from . import db
from .catalog import GENERICS, label_bn, resolve_generic
from .ranking import haversine_km, score_offers

TRANSITIONS: dict[str, set[str]] = {
    "placed": {"confirmed", "cancelled"},
    "confirmed": {"ready", "cancelled"},
    "ready": {"collected", "delivered"},
    "collected": set(), "delivered": set(), "cancelled": set(),
}
STATUS_BN = {"placed": "অর্ডার হয়েছে", "confirmed": "দোকান নিশ্চিত করেছে", "ready": "প্রস্তুত",
             "collected": "সংগ্রহ করা হয়েছে", "delivered": "পৌঁছে দেওয়া হয়েছে", "cancelled": "বাতিল"}


class MarketError(ValueError):
    pass


def _coords(district: str) -> tuple[float, float] | None:
    hit = lookup_district(district or "")
    return (hit[2], hit[3]) if hit else None


def _listing_provenance(p: dict, d: dict) -> dict:
    return {
        "value": p["price_bdt"], "unit": f"BDT per {p['pack_size']:g} {p['pack_unit']} pack",
        "source_type": "listing",
        "source_id": f"listing:{p['product_id']}",
        "source_title": f"{d['name']} ({d['district']}) — dealer listing" + (" [DEMO]" if p["is_demo"] else ""),
        "locator": f"product {p['product_id']}, updated {p['updated_at'][:10]}",
        "retrieved_at": db.now(),
        "confidence": "low" if p["is_demo"] else "medium",
    }


def find_inputs(product: str, district: str, quantity: float | None = None, limit: int = 3) -> dict:
    """Agent tool. Ranked offers for one input near the farm's district.

    Args:
        product: generic name, English or Bangla ("urea", "mancozeb", "ইউরিয়া").
        district: the farm's district (canonical English, as geocode returns).
        quantity: optional amount needed, in the product's unit (kg or l),
            copied from a tool result (finance_projection item qty, a KB dose ×
            area already computed by a tool) — never estimated.
    """
    generic = resolve_generic(product)
    if not generic:
        return {"error": f"unknown input '{product}'",
                "known_inputs": sorted(GENERICS), "note": "Say the marketplace does not list it."}
    here = _coords(district)
    if not here:
        return {"error": f"unknown district '{district}'"}
    found = db.rows(
        "SELECT p.*, d.name AS dealer_name, d.district AS dealer_district, d.upazila, d.lat, d.lon, "
        "d.verified, d.completed_orders, d.is_demo AS dealer_is_demo "
        "FROM products p JOIN dealers d ON d.dealer_id = p.dealer_id "
        "WHERE p.generic = ? AND p.stock_packs > 0", (generic,))
    offers, need = [], {}
    for r in found:
        lat, lon = (r["lat"], r["lon"]) if r["lat"] is not None else (_coords(r["dealer_district"]) or here)
        offer = {
            "product_id": r["product_id"], "dealer_id": r["dealer_id"], "dealer_name": r["dealer_name"],
            "dealer_district": r["dealer_district"], "upazila": r["upazila"],
            "brand_name": r["brand_name"], "pack_size": r["pack_size"], "pack_unit": r["pack_unit"],
            "price_bdt": r["price_bdt"], "unit_price": money.unit_price(r["price_bdt"], r["pack_size"]),
            "km": round(haversine_km(here[0], here[1], lat, lon), 1),
            "stock_packs": r["stock_packs"], "verified": bool(r["verified"]),
            "completed_orders": r["completed_orders"], "is_demo": bool(r["is_demo"] or r["dealer_is_demo"]),
            "provenance": _listing_provenance(r, {"name": r["dealer_name"], "district": r["dealer_district"]}),
        }
        if quantity:
            need[r["product_id"]] = money.packs_needed(quantity, r["pack_size"])
            offer["for_quantity"] = money.cost_for_quantity(quantity, r["pack_size"], r["price_bdt"])
        offers.append(offer)
    ranked = score_offers(offers, need)[: max(1, min(limit, 5))]
    result = {
        "product": generic, "product_bn": label_bn(generic), "district": district,
        "offers": ranked,
        "ranking_rule": "price 40 + distance 30 + stock 15 + trust 15; no paid placement",
        "narration_rules": (
            "Quote each offer's price and distance exactly as given. If is_demo is true, say "
            "'ডেমো দোকান' next to that dealer. The farmer orders from the app button, USSD "
            "menu 4, or by SMS; you do not place orders."
        ),
    }
    if not ranked:
        result["note"] = "No dealer within 80 km lists this input. Say so; do not guess a price."
    return result


def _dealer(dealer_id: str) -> dict:
    d = db.row("SELECT * FROM dealers WHERE dealer_id = ?", (dealer_id,))
    if not d:
        raise MarketError("unknown dealer")
    return d


def place_order(farm_id: str, product_id: str, packs: int, payment: str = "cod",
                channel: str = "web") -> dict:
    """One product line per order (a farmer buys one input at a time on a
    button phone); the web can place several orders."""
    if payment not in ("cod", "caas"):
        raise MarketError("payment must be cod or caas")
    p = db.row("SELECT * FROM products WHERE product_id = ?", (product_id,))
    if not p:
        raise MarketError("unknown product")
    if packs > p["stock_packs"]:
        raise MarketError(f"only {p['stock_packs']} packs in stock")
    dealer = _dealer(p["dealer_id"])
    label = label_bn(p["generic"])
    brand = p["brand_name"] if label in p["brand_name"] else f"{label} {p['brand_name']}"
    name = f"{brand}, {p['pack_size']:g} {p['pack_unit']}"
    totals = money.order_totals([{"product_id": product_id, "name": name, "packs": packs,
                                  "price_per_pack": p["price_bdt"]}]).as_dict()
    ts = db.now()
    order_id = db.execute(
        "INSERT INTO orders (farm_id, dealer_id, totals_json, payment, status, channel, is_demo, "
        "created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (farm_id, dealer["dealer_id"], db.dumps(totals), payment, "placed", channel,
         int(p["is_demo"] or dealer["is_demo"]), ts, ts))
    db.execute("UPDATE products SET stock_packs = stock_packs - ? WHERE product_id = ?", (packs, product_id))
    order = get_order(order_id)
    _notify_dealer_new_order(dealer, order)
    _notify_farmer(order)
    return order


def get_order(order_id: int) -> dict:
    o = db.row("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    if not o:
        raise MarketError("unknown order")
    o["totals"] = json.loads(o.pop("totals_json"))
    o["status_bn"] = STATUS_BN[o["status"]]
    d = _dealer(o["dealer_id"])
    o["dealer"] = {"name": d["name"], "district": d["district"], "upazila": d["upazila"],
                   "is_demo": bool(d["is_demo"])}
    return o


def farm_orders(farm_id: str) -> list[dict]:
    return [get_order(r["order_id"]) for r in
            db.rows("SELECT order_id FROM orders WHERE farm_id = ? ORDER BY order_id DESC", (farm_id,))]


def set_order_status(order_id: int, status: str, *, dealer_id: str | None = None,
                     farm_id: str | None = None) -> dict:
    """Dealer moves an order forward; a farmer may only cancel their own."""
    o = get_order(order_id)
    if dealer_id is not None and o["dealer_id"] != dealer_id:
        raise MarketError("not this dealer's order")
    if farm_id is not None and (o["farm_id"] != farm_id or status != "cancelled"):
        raise MarketError("a farmer can only cancel their own order")
    if status not in TRANSITIONS.get(o["status"], set()):
        raise MarketError(f"cannot go from {o['status']} to {status}")
    db.execute("UPDATE orders SET status = ?, updated_at = ? WHERE order_id = ?", (status, db.now(), order_id))
    if status == "cancelled":  # give the stock back
        for line in o["totals"]["lines"]:
            db.execute("UPDATE products SET stock_packs = stock_packs + ? WHERE product_id = ?",
                       (line["packs"], line["product_id"]))
    if status in ("collected", "delivered"):
        db.execute("UPDATE dealers SET completed_orders = completed_orders + 1 WHERE dealer_id = ?",
                   (o["dealer_id"],))
    updated = get_order(order_id)
    _notify_farmer(updated)
    return updated


# --- dealers ------------------------------------------------------------------


def register_dealer(name: str, district: str, msisdn: str, upazila: str | None = None,
                    *, is_demo: bool = False, verified: bool = False, dealer_id: str | None = None) -> dict:
    from backend.channels.identity import normalise
    if not _coords(district):
        raise MarketError(f"unknown district '{district}'")
    local = normalise(msisdn)
    dealer_id = dealer_id or f"d-{db.new_token()[:8]}"
    token = db.new_token()
    lat, lon = _coords(district)
    db.execute(
        "INSERT INTO dealers (dealer_id, name, district, upazila, msisdn, lat, lon, verified, token, "
        "is_demo, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (dealer_id, name.strip(), lookup_district(district)[0], upazila, local, lat, lon,
         int(verified), token, int(is_demo), db.now()))
    return {"dealer_id": dealer_id, "token": token}


def dealer_by_token(token: str) -> dict:
    d = db.row("SELECT * FROM dealers WHERE token = ?", (token or "",))
    if not d:
        raise MarketError("unknown dealer token")
    return d


def upsert_product(dealer_id: str, generic: str, brand_name: str, pack_size: float, pack_unit: str,
                   price_bdt: float, stock_packs: int, *, price_source: str | None = None,
                   product_id: str | None = None, is_demo: bool = False) -> dict:
    g = resolve_generic(generic)
    if not g:
        raise MarketError(f"unknown input '{generic}'")
    if pack_size <= 0 or price_bdt <= 0 or stock_packs < 0:
        raise MarketError("pack size and price must be positive, stock non-negative")
    _dealer(dealer_id)
    product_id = product_id or f"p-{db.new_token()[:8]}"
    db.execute(
        "INSERT INTO products (product_id, dealer_id, generic, brand_name, pack_size, pack_unit, price_bdt, "
        "stock_packs, price_source, updated_at, is_demo) VALUES (?,?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(product_id) DO UPDATE SET brand_name=excluded.brand_name, pack_size=excluded.pack_size, "
        "pack_unit=excluded.pack_unit, price_bdt=excluded.price_bdt, stock_packs=excluded.stock_packs, "
        "price_source=excluded.price_source, updated_at=excluded.updated_at",
        (product_id, dealer_id, g, brand_name, pack_size, pack_unit, price_bdt, stock_packs,
         price_source, db.now(), int(is_demo)))
    return db.row("SELECT * FROM products WHERE product_id = ?", (product_id,))


def dealer_view(dealer: dict) -> dict:
    return {
        "dealer": {k: dealer[k] for k in ("dealer_id", "name", "district", "upazila", "verified",
                                           "completed_orders", "is_demo")},
        "products": db.rows("SELECT * FROM products WHERE dealer_id = ? ORDER BY generic", (dealer["dealer_id"],)),
        "orders": [get_order(r["order_id"]) for r in db.rows(
            "SELECT order_id FROM orders WHERE dealer_id = ? ORDER BY order_id DESC LIMIT 50",
            (dealer["dealer_id"],))],
    }


# --- SMS notifications ------------------------------------------------------------


def _send_to_number(local_msisdn: str, text: str, *, demo: bool = False) -> None:
    """Dealers and buyers are not farms, but reuse the same send path: they get
    a contacts row keyed by the same salted-hash id their number would have.

    Demo accounts have made-up numbers that may belong to a real stranger, so
    with a LIVE provider their messages are logged as skipped, never sent."""
    from backend.channels import sms, sms_text
    from backend.channels.identity import farm_id_for, mask
    from backend.memory import store
    fid = farm_id_for(local_msisdn)
    store.upsert_contact(fid, local_msisdn, mask(local_msisdn), "market")
    if demo and sms.provider().mode == "live":
        store.log_sms(fid, "out", text, sms_text.segments(text), sms.provider().name, "skipped_demo")
        return
    sms.send_sms(fid, text)


def _notify_dealer_new_order(dealer: dict, order: dict) -> None:
    line = order["totals"]["lines"][0]
    _send_to_number(dealer["msisdn"], demo=bool(dealer["is_demo"]), text=(
        f"নতুন অর্ডার #{order['order_id']}: {line['name']} × {line['packs']}, "
        f"৳{order['totals']['farmer_pays']:,.0f} ({'নগদে' if order['payment'] == 'cod' else 'মোবাইল ব্যালেন্স'})।\n"
        f"নিশ্চিত করতে লিখুন: হ্যাঁ {order['order_id']}\nবাতিল: না {order['order_id']}"
    ))


def _notify_farmer(order: dict) -> None:
    from backend.channels import sms
    d = order["dealer"]
    demo = " (ডেমো দোকান)" if d["is_demo"] else ""
    sms.send_sms(order["farm_id"], (
        f"অর্ডার #{order['order_id']}: {order['status_bn']}।\n"
        f"দোকান: {d['name']}{demo}, {d['upazila'] or d['district']}\n"
        f"মোট ৳{order['totals']['farmer_pays']:,.0f}"
    ))
