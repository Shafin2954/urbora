"""USSD sub-menus for the marketplaces (main menu 4 and 5).

Same contract as backend/channels/ussd.py: a handler takes (state, input, ctx)
and returns (screen, state, action). Screens read only the local DB (offers,
price guide), so they answer instantly; placing the order or the listing is an
action the USSD runtime runs in the background, which then texts the farmer.
"""

from __future__ import annotations

from backend.channels.sms_text import CROP_BN
from backend.channels.ussd import Screen, main_menu
from backend.finance import market as money

from .catalog import label_bn

_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
INPUT_CHOICES = ["urea", "tsp", "mop", "mancozeb", "tricyclazole", "carbendazim"]
CROP_CHOICES = ["boro_rice", "aman_rice", "potato", "mustard", "lentil"]
NO_DISTRICT = Screen("আগে মূল মেনুর 1 (নতুন পরামর্শ) থেকে আপনার জেলা দিন।", end=True)


def _d(text: str | None) -> str:
    return (text or "").strip().translate(_BN_DIGITS)


def _home(ctx) -> tuple[Screen, dict, None]:
    return main_menu(ctx), {"at": "main"}, None


def _district(ctx) -> str | None:
    return (ctx.profile or {}).get("district")


# --- 4. inputs ----------------------------------------------------------------------


def _inputs_menu() -> Screen:
    lines = ["কী কিনবেন?"] + [f"{i}. {label_bn(g)}" for i, g in enumerate(INPUT_CHOICES, 1)] + ["0. পিছনে"]
    return Screen("\n".join(lines))


def _offer_line(i: int, o: dict) -> str:
    demo = " ডেমো" if o["is_demo"] else ""
    return f"{i}. {o['dealer_name'][:14]}{demo} {o['pack_size']:g}{o['pack_unit']} ৳{o['price_bdt']:g}, {o['km']:g}কিমি"


def inputs(state: dict, text: str | None, ctx) -> tuple[Screen, dict, dict | None]:
    from .inputs import find_inputs

    step, inp = state.get("step"), _d(text)
    if text is None:
        if not _district(ctx):
            return NO_DISTRICT, {"at": "main"}, None
        return _inputs_menu(), {"at": "inputs", "sub": "inputs", "step": "product"}, None
    if inp == "0" and step in ("product", "offer"):
        return _home(ctx)

    if step == "product":
        if not (inp.isdigit() and 1 <= int(inp) <= len(INPUT_CHOICES)):
            return Screen("ভুল বাছাই।\n" + _inputs_menu().text), state, None
        generic = INPUT_CHOICES[int(inp) - 1]
        offers = find_inputs(generic, _district(ctx)).get("offers") or []
        if not offers:
            return Screen(f"কাছে কোনো দোকানে {label_bn(generic)} তালিকাভুক্ত নেই।", end=True), state, None
        keep = [{k: o[k] for k in ("product_id", "dealer_name", "pack_size", "pack_unit", "price_bdt",
                                   "km", "is_demo", "brand_name")} for o in offers[:3]]
        lines = [f"{label_bn(generic)}: দোকান বাছুন"] + [_offer_line(i, o) for i, o in enumerate(keep, 1)]
        return Screen("\n".join(lines + ["0. পিছনে"])), {**state, "step": "offer", "generic": generic,
                                                         "offers": keep}, None

    if step == "offer":
        offers = state.get("offers") or []
        if not (inp.isdigit() and 1 <= int(inp) <= len(offers)):
            return Screen("ভুল বাছাই। দোকানের নম্বর দিন।"), state, None
        return Screen("কয়টি প্যাকেট? সংখ্যা লিখুন"), {**state, "step": "packs", "pick": offers[int(inp) - 1]}, None

    if step == "packs":
        if not inp.isdigit() or not 1 <= int(inp) <= 999:
            return Screen("সঠিক সংখ্যা দিন। কয়টি প্যাকেট?"), state, None
        pick, packs = state["pick"], int(inp)
        totals = money.order_totals([{"product_id": pick["product_id"], "name": pick["brand_name"],
                                      "packs": packs, "price_per_pack": pick["price_bdt"]}])
        text_ = (f"{label_bn(state['generic'])} {pick['pack_size']:g}{pick['pack_unit']} × {packs}\n"
                 f"মোট ৳{float(totals.subtotal):,.0f}, দোকানে নগদে\n1. অর্ডার করুন\n2. বাতিল")
        return Screen(text_), {**state, "step": "confirm", "packs": packs}, None

    if step == "confirm":
        if inp == "1":
            action = {"kind": "market", "op": "order", "product_id": state["pick"]["product_id"],
                      "packs": state["packs"]}
            return Screen("অর্ডার পাঠানো হয়েছে। দোকান নিশ্চিত করলে SMS পাবেন।", end=True), {"at": "main"}, action
        return Screen("বাতিল করা হয়েছে।", end=True), {"at": "main"}, None

    return _home(ctx)


# --- 5. produce ---------------------------------------------------------------------


def _crop_menu() -> Screen:
    lines = ["কোন ফসল বিক্রি করবেন?"] + [f"{i}. {CROP_BN[c]}" for i, c in enumerate(CROP_CHOICES, 1)] + ["0. পিছনে"]
    return Screen("\n".join(lines))


def produce(state: dict, text: str | None, ctx) -> tuple[Screen, dict, dict | None]:
    from .produce import guide_sms_line, price_guide

    step, inp = state.get("step"), _d(text)
    if text is None:
        if not _district(ctx):
            return NO_DISTRICT, {"at": "main"}, None
        return _crop_menu(), {"at": "produce", "sub": "produce", "step": "crop"}, None
    if inp == "0" and step == "crop":
        return _home(ctx)

    if step == "crop":
        if not (inp.isdigit() and 1 <= int(inp) <= len(CROP_CHOICES)):
            return Screen("ভুল বাছাই।\n" + _crop_menu().text), state, None
        return Screen("কত কেজি? সংখ্যা লিখুন"), {**state, "step": "qty", "crop": CROP_CHOICES[int(inp) - 1]}, None

    if step == "qty":
        try:
            qty = float(inp)
        except ValueError:
            qty = 0
        if not 0 < qty <= 1_000_000:
            return Screen("সঠিক সংখ্যা দিন। কত কেজি?"), state, None
        guide = guide_sms_line(price_guide(state["crop"]))
        return (Screen("\n".join(filter(None, [guide, "প্রতি কেজি কত টাকা চান?", "না জানলে * চাপুন"]))),
                {**state, "step": "price", "qty": qty}, None)

    if step == "price":
        price = None
        if inp != "*":
            try:
                price = float(inp)
            except ValueError:
                price = -1
            if price <= 0:
                return Screen("সঠিক দাম দিন, অথবা * চাপুন"), state, None
        ask = f", ৳{price:g}/কেজি" if price else ", দাম ক্রেতা বলবেন"
        return (Screen(f"{CROP_BN[state['crop']]} {state['qty']:g} কেজি{ask}\n1. তালিকা করুন\n2. বাতিল"),
                {**state, "step": "confirm", "price": price}, None)

    if step == "confirm":
        if inp == "1":
            action = {"kind": "market", "op": "list", "crop": state["crop"], "qty_kg": state["qty"],
                      "price": state.get("price")}
            return Screen("তালিকা পাঠানো হয়েছে। ক্রেতার অফার SMS-এ আসবে।", end=True), {"at": "main"}, action
        return Screen("বাতিল করা হয়েছে।", end=True), {"at": "main"}, None

    return _home(ctx)


SUBMENUS = {"inputs": inputs, "produce": produce}


def run_market_action(local_msisdn: str, farm_id: str, action: dict) -> None:
    """Run a marketplace action requested from USSD; failures are texted."""
    from backend.channels import sms

    from .inputs import MarketError, place_order
    from .produce import ProduceError, create_listing, guide_sms_line

    try:
        if action["op"] == "order":
            place_order(farm_id, action["product_id"], action["packs"], "cod", channel="ussd")
        elif action["op"] == "list":
            listing = create_listing(farm_id, action["crop"], action["qty_kg"], action.get("price"), channel="ussd")
            guide = guide_sms_line(listing["price_guide"])
            sms.send_sms(farm_id, f"তালিকা #{listing['listing_id']} হয়েছে। কাছের ক্রেতারা অফার পাঠাবেন।"
                                  + (f"\n{guide}" if guide else ""))
    except (MarketError, ProduceError) as exc:
        sms.send_sms(farm_id, f"করা যায়নি: {exc}")
