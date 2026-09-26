"""Input + produce marketplaces: ranking, orders, offers, SMS/USSD, routes."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from backend.channels import sms
from backend.channels.identity import farm_id_for
from backend.channels.ussd import UssdContext, step
from backend.market import db, inputs, produce, seed_demo, sms_commands
from backend.market.ranking import score_offers
from backend.memory import store

FARMER = "01812345678"
DEALER_1 = "01300000011"


class Recorder:
    name, mode = "rec", "simulator"

    def __init__(self):
        self.sent = []

    def send(self, local, text):
        self.sent.append((local, text))
        return sms.SendResult(self.name, "sent")

    def to(self, number):
        return [t for n, t in self.sent if n == number]


@pytest.fixture()
def rec(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "market.db")
    monkeypatch.setenv("CHANNEL_ID_SALT", "test-salt")
    monkeypatch.setenv("MARKET_COMMISSION_PCT", "5")
    monkeypatch.setenv("PRODUCE_FEE_PCT", "2")
    r = Recorder()
    sms.set_provider(r)
    seed_demo.seed()
    fid = farm_id_for(FARMER)
    store.upsert_contact(fid, FARMER, "***678", "sms")
    store.save_farm(fid, {"district": "Rajshahi"})
    yield r
    sms.set_provider(None)


# --- ranking ------------------------------------------------------------------------

def _offer(pid, unit_price, km, stock=10, verified=True, orders=0):
    return {"product_id": pid, "dealer_id": pid, "unit_price": unit_price, "km": km,
            "stock_packs": stock, "verified": verified, "completed_orders": orders}


def test_ranking_is_explainable_and_deterministic():
    ranked = score_offers([_offer("a", 30, 5), _offer("b", 27, 40), _offer("c", 27, 40)])
    assert [o["dealer_id"] for o in ranked] == ["a", "b", "c"]
    assert ranked[1]["components"]["price"] == 40.0 and ranked[0]["components"]["price"] == 36.0
    assert set(ranked[0]["components"]) == {"price", "distance", "stock", "trust"}


def test_far_dealers_are_dropped_and_low_stock_is_penalised():
    ranked = score_offers([_offer("near", 27, 10, stock=1), _offer("far", 20, 120)], {"near": 4})
    assert [o["dealer_id"] for o in ranked] == ["near"]
    assert ranked[0]["components"]["stock"] == 3.75


# --- find_inputs ----------------------------------------------------------------------

def test_find_inputs_quotes_cited_fertiliser_and_labels_demo(rec):
    out = inputs.find_inputs("ইউরিয়া", "Rajshahi", quantity=137.5)
    assert out["product"] == "urea" and len(out["offers"]) == 3
    top = out["offers"][0]
    assert top["dealer_district"] == "Rajshahi" and top["price_bdt"] == 1350 and top["unit_price"] == 27.0
    assert top["is_demo"] and top["provenance"]["source_type"] == "listing"
    assert "[DEMO]" in top["provenance"]["source_title"]
    assert top["for_quantity"] == {"packs": 3, "total_bdt": 4050.0,
                                   "formula": "ceil(137.5 / 50) = 3 packs × ৳1350 = ৳4050.00"}
    assert out["offers"] == sorted(out["offers"], key=lambda o: -o["score"])


def test_find_inputs_is_honest_about_unknowns(rec):
    assert "error" in inputs.find_inputs("glyphosate", "Rajshahi")
    assert "error" in inputs.find_inputs("urea", "Atlantis")
    far = inputs.find_inputs("urea", "Cox's Bazar")
    assert far["offers"] == [] and "do not guess" in far["note"]


# --- orders ----------------------------------------------------------------------------

def test_order_lifecycle_over_sms(rec):
    fid = farm_id_for(FARMER)
    order = inputs.place_order(fid, "demo-d1-urea", 2, channel="ussd")
    assert order["status"] == "placed" and order["totals"]["farmer_pays"] == 2700.0
    assert order["totals"]["commission"] == 135.0 and order["totals"]["dealer_payout"] == 2565.0
    assert db.row("SELECT stock_packs FROM products WHERE product_id='demo-d1-urea'")["stock_packs"] == 38
    assert "হ্যাঁ 1" in rec.to(DEALER_1)[-1]
    assert "অর্ডার #1: অর্ডার হয়েছে" in rec.to(FARMER)[-1] and "ডেমো দোকান" in rec.to(FARMER)[-1]

    # A farmer texting "হ্যাঁ 1" is not a dealer: the agent handles it.
    assert sms_commands.try_handle(FARMER, "হ্যাঁ 1") is None
    reply = sms_commands.try_handle(DEALER_1, "হ্যাঁ ১")
    assert "দোকান নিশ্চিত করেছে" in reply
    assert "দোকান নিশ্চিত করেছে" in rec.to(FARMER)[-1]
    assert "করা যায়নি" in sms_commands.try_handle(DEALER_1, "হ্যাঁ 1")  # already confirmed
    sms_commands.try_handle(DEALER_1, "প্রস্তুত 1")
    sms_commands.try_handle(DEALER_1, "দেওয়া 1")
    assert inputs.get_order(1)["status"] == "delivered"
    assert db.row("SELECT completed_orders FROM dealers WHERE dealer_id='demo-d1'")["completed_orders"] == 1


def test_cancel_restores_stock_and_only_the_owner_may_cancel(rec):
    fid = farm_id_for(FARMER)
    inputs.place_order(fid, "demo-d1-mop", 5)
    with pytest.raises(inputs.MarketError):
        inputs.set_order_status(1, "cancelled", farm_id="ph-someone-else")
    with pytest.raises(inputs.MarketError):
        inputs.set_order_status(1, "confirmed", farm_id=fid)
    inputs.set_order_status(1, "cancelled", farm_id=fid)
    assert db.row("SELECT stock_packs FROM products WHERE product_id='demo-d1-mop'")["stock_packs"] == 40


def test_order_beyond_stock_is_refused(rec):
    with pytest.raises(inputs.MarketError):
        inputs.place_order(farm_id_for(FARMER), "demo-d1-urea", 41)


def test_live_gateway_never_texts_demo_numbers(rec):
    class Live(Recorder):
        mode = "live"

    live = Live()
    sms.set_provider(live)
    inputs.place_order(farm_id_for(FARMER), "demo-d1-urea", 1)
    assert live.to(DEALER_1) == []
    assert store.list_sms(farm_id_for(DEALER_1))[0]["status"] == "skipped_demo"
    assert live.to(FARMER)  # the real farmer still hears about their order


# --- produce --------------------------------------------------------------------------

def test_sell_by_sms_offer_and_accept(rec):
    reply = sms_commands.try_handle(FARMER, "বিক্রি আলু ৫০০ কেজি ২২ টাকা")
    assert reply.startswith("তালিকা #1 হয়েছে") and "খামার-দাম ৳7/কেজি" in reply
    assert any("নতুন ফসল #1" in t for t in rec.to("01300000021"))  # nearby buyer told

    o1 = produce.make_offer("demo-b1", 1, 21)
    produce.make_offer("demo-b2", 1, 20)
    assert "আপনি পাবেন ৳10,500" in rec.to(FARMER)[-2] and "গ্রহণ 1" in rec.to(FARMER)[-2]
    assert o1["totals"] == {"farmer_receives": 10500.0, "fee_pct": 2.0, "platform_fee": 210.0,
                            "buyer_pays": 10710.0, "formula": o1["totals"]["formula"]}

    assert sms_commands.try_handle("01999999999", "গ্রহণ 1").startswith("অফার #1: করা যায়নি")
    assert "গৃহীত" in sms_commands.try_handle(FARMER, "গ্রহণ 1")
    listing = produce.get_listing(1)
    assert listing["status"] == "sold"
    assert [o["status"] for o in listing["offers"]] == ["accepted", "rejected"]
    assert "01300000021" in rec.to(FARMER)[-1] and "আসল নম্বর নয়" in rec.to(FARMER)[-1]
    assert FARMER in rec.to("01300000021")[-1] and "৳10,710" in rec.to("01300000021")[-1]


def test_sell_needs_a_known_crop_and_district():
    assert "ফসলের নাম বুঝিনি" in sms_commands.try_handle(FARMER, "বিক্রি পেঁপে 10 কেজি")


def test_sell_without_a_saved_district_asks_for_it(rec):
    other = "01712345678"
    assert "জেলার নাম সহ" in sms_commands.try_handle(other, "বিক্রি আলু 100 কেজি")
    assert sms_commands.try_handle(other, "বিক্রি আলু 100 কেজি রাজশাহী").startswith("তালিকা #")


def test_buyers_never_see_the_farmer_before_acceptance(rec):
    produce.create_listing(farm_id_for(FARMER), "potato", 100)
    view = produce.buyer_view(produce.buyer_by_token(db.row("SELECT token FROM buyers WHERE buyer_id='demo-b1'")["token"]))
    assert view["listings"] and "farm_id" not in view["listings"][0]


def test_ordinary_messages_fall_through_to_the_agent(rec):
    assert sms_commands.try_handle(FARMER, "আমার ধানে পোকা") is None


# --- USSD sub-menus ------------------------------------------------------------------------

def _ctx():
    from backend.market.ussd_menus import SUBMENUS
    return UssdContext(brand="B", farm_id=farm_id_for(FARMER), profile={"district": "Rajshahi"}, submenus=SUBMENUS)


def test_ussd_buy_urea(rec):
    c = _ctx()
    screen, state, _ = step(None, None, c)
    for t in ["4", "1", "1", "2"]:
        screen, state, action = step(state, t, c)
    assert "মোট ৳2,700" in screen.text
    screen, state, action = step(state, "1", c)
    assert screen.end and action == {"kind": "market", "op": "order", "product_id": "demo-d1-urea", "packs": 2}
    from backend.market.ussd_menus import run_market_action
    run_market_action(FARMER, farm_id_for(FARMER), action)
    assert inputs.farm_orders(farm_id_for(FARMER))[0]["channel"] == "ussd"


def test_ussd_sell_potato_shows_the_price_guide(rec):
    c = _ctx()
    screen, state, _ = step(None, None, c)
    for t in ["5", "3", "500"]:
        screen, state, action = step(state, t, c)
    assert "খামার-দাম ৳7/কেজি" in screen.text
    screen, state, _ = step(state, "*", c)
    assert "দাম ক্রেতা বলবেন" in screen.text
    screen, state, action = step(state, "1", c)
    assert action["op"] == "list" and action["price"] is None


def test_ussd_market_without_a_district_sends_the_farmer_to_intake(rec):
    from backend.market.ussd_menus import SUBMENUS
    c = UssdContext(brand="B", farm_id="x", profile=None, submenus=SUBMENUS)
    _, state, _ = step(None, None, c)
    screen, _, _ = step(state, "4", c)
    assert screen.end and "জেলা" in screen.text


# --- routes -----------------------------------------------------------------------------------

def test_dealer_routes_need_the_dealer_token(rec):
    from backend.api.main import app
    client = TestClient(app)
    assert client.get("/api/market/dealer").status_code == 401
    reg = client.post("/api/market/dealers", json={"name": "Real shop", "district": "Rajshahi",
                                                   "msisdn": "01711111111"}).json()
    h = {"X-Dealer-Token": reg["token"]}
    p = client.put("/api/market/dealer/products", headers=h, json={
        "generic": "urea", "brand_name": "Urea", "pack_size": 50, "pack_unit": "kg",
        "price_bdt": 1400, "stock_packs": 10}).json()
    assert p["is_demo"] == 0
    stolen = client.put("/api/market/dealer/products", headers=h, json={
        "generic": "urea", "brand_name": "x", "pack_size": 50, "pack_unit": "kg", "price_bdt": 1,
        "stock_packs": 1, "product_id": "demo-d1-urea"})
    assert stolen.status_code == 403
    assert client.get("/api/market/dealer", headers=h).json()["dealer"]["verified"] == 0


def test_buyer_offer_route(rec):
    from backend.api.main import app
    client = TestClient(app)
    produce.create_listing(farm_id_for(FARMER), "boro_rice", 2000, 30)
    token = db.row("SELECT token FROM buyers WHERE buyer_id='demo-b2'")["token"]
    r = client.post("/api/market/buyer/offers", headers={"X-Buyer-Token": token},
                    json={"listing_id": 1, "price_per_kg": 29})
    assert r.status_code == 200 and r.json()["totals"]["farmer_receives"] == 58000.0
    bad = client.post("/api/market/buyer/offers", headers={"X-Buyer-Token": token},
                      json={"listing_id": 1, "price_per_kg": 29, "qty_kg": 5000})
    assert bad.status_code == 422


def test_inbound_sms_command_skips_the_agent(rec, monkeypatch):
    from backend.agent import loop
    from backend.channels import flows
    monkeypatch.setattr(loop, "run_turn", lambda *a, **k: pytest.fail("agent must not run"))
    asyncio.run(flows.handle_inbound_sms(FARMER, "বিক্রি আলু 100 কেজি", "rec"))
    assert rec.to(FARMER)[-1].startswith("তালিকা #1 হয়েছে")
