"""USSD sub-menus for the marketplaces (main menu 5 and 6).

Same contract as backend/channels/ussd.py: a handler takes (state, input, ctx)
and returns (screen, state, action). Screens read only the local DB (offers,
price guide), so they answer instantly; placing the order or the listing is an
action the USSD runtime runs in the background, which then texts the farmer.
Screens use the shared pager, so each fits one 80-unit Bangla USSD screen;
9 = more, 0 = back, as everywhere.
"""

from __future__ import annotations

from backend.channels.sms_text import CROP_BN
from backend.channels.ussd import BAD, Screen, clip, main_menu, paged, pick_paged, with_note
from backend.finance import market as money

from .catalog import label_bn

_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
INPUT_CHOICES = ["urea", "tsp", "mop", "mancozeb", "tricyclazole", "carbendazim"]
CROP_CHOICES = ["boro_rice", "aman_rice", "potato", "mustard", "lentil"]
NO_DISTRICT = Screen("আগে মূল মেনুর 1 (ফসল পরামর্শ) থেকে আপনার জেলা দিন।", end=True)
PRODUCT_TITLE = "কী কিনবেন?"
CROP_TITLE = "কোন ফসল বেচবেন?"


def _d(text: str | None) -> str:
    return (text or "").strip().translate(_BN_DIGITS)


def _home(ctx) -> tuple[Screen, dict, None]:
    return main_menu(ctx), {"at": "main"}, None


def _district(ctx) -> str | None:
    return (ctx.profile or {}).get("district")


def _menu_step(title: str, labels: list[str], state: dict, page_key: str, inp: str):
    """Shared handling of a paged pick: returns (kind, value, screen-or-None, state)."""
    kind, val = pick_paged(title, labels, state.get(page_key, 0), inp)
    if kind == "page":
        return kind, val, paged(title, labels, val), {**state, page_key: val}
    if kind == "bad":
        return kind, val, Screen(with_note(paged(title, labels, state.get(page_key, 0)).text, BAD)), state
    return kind, val, None, state


# --- 5. inputs ----------------------------------------------------------------------


def _product_labels() -> list[str]:
    return [label_bn(g) for g in INPUT_CHOICES]


def _offer_label(o: dict) -> str:
    # Rule 16: a demo dealer is labelled on every line it appears.
    demo = " ডেমো" if o["is_demo"] else ""
    return f"{o['dealer_name'][:10]}{demo} ৳{o['price_bdt']:g}/{o['pack_size']:g}{o['pack_unit']} {o['km']:g}কিমি"


def _offers_title(generic: str) -> str:
    return f"{label_bn(generic)}: দোকান"


def inputs(state: dict, text: str | None, ctx) -> tuple[Screen, dict, dict | None]:
    from .inputs import find_inputs

    step, inp = state.get("step"), _d(text)
    if text is None:
        if not _district(ctx):
            return NO_DISTRICT, {"at": "main"}, None
        return paged(PRODUCT_TITLE, _product_labels(), 0), {"at": "inputs", "sub": "inputs", "step": "product"}, None

    if step == "product":
        kind, val, screen, state = _menu_step(PRODUCT_TITLE, _product_labels(), state, "ppage", inp)
        if kind == "back":
            return _home(ctx)
        if screen:
            return screen, state, None
        generic = INPUT_CHOICES[val]
        offers = find_inputs(generic, _district(ctx)).get("offers") or []
        if not offers:
            return Screen(f"কাছে কোনো দোকানে {label_bn(generic)} তালিকাভুক্ত নেই।", end=True), state, None
        keep = [{k: o[k] for k in ("product_id", "dealer_name", "pack_size", "pack_unit", "price_bdt",
                                   "km", "is_demo", "brand_name")} for o in offers[:3]]
        return (paged(_offers_title(generic), [_offer_label(o) for o in keep], 0),
                {**state, "step": "offer", "generic": generic, "offers": keep, "opage": 0}, None)

    if step == "offer":
        offers = state.get("offers") or []
        kind, val, screen, state = _menu_step(_offers_title(state["generic"]),
                                              [_offer_label(o) for o in offers], state, "opage", inp)
        if kind == "back":
            return paged(PRODUCT_TITLE, _product_labels(), 0), {**state, "step": "product", "ppage": 0}, None
        if screen:
            return screen, state, None
        return Screen("কয়টি প্যাকেট?\nসংখ্যা লিখুন"), {**state, "step": "packs", "pick": offers[val]}, None

    if step == "packs":
        if not inp.isdigit() or not 1 <= int(inp) <= 999:
            return Screen("ভুল সংখ্যা! কয়টি প্যাকেট?"), state, None
        pick, packs = state["pick"], int(inp)
        totals = money.order_totals([{"product_id": pick["product_id"], "name": pick["brand_name"],
                                      "packs": packs, "price_per_pack": pick["price_bdt"]}])
        head = (f"{label_bn(state['generic'])} {pick['pack_size']:g}{pick['pack_unit']} × {packs}\n"
                f"মোট ৳{float(totals.subtotal):,.0f}, দোকানে নগদে")
        return Screen(clip(head, "1. অর্ডার করুন\n2. বাতিল")), {**state, "step": "confirm", "packs": packs}, None

    if step == "confirm":
        if inp == "1":
            action = {"kind": "market", "op": "order", "product_id": state["pick"]["product_id"],
                      "packs": state["packs"]}
            return Screen("অর্ডার গেছে। দোকান নিশ্চিত করলে SMS পাবেন।", end=True), {"at": "main"}, action
        return Screen("বাতিল করা হয়েছে।", end=True), {"at": "main"}, None

    return _home(ctx)


# --- 6. produce ---------------------------------------------------------------------


def _crop_labels() -> list[str]:
    return [CROP_BN[c] for c in CROP_CHOICES]


def guide_short(guide: dict | None) -> str:
    """The price guide as one short screen line; the dated, sourced version goes by SMS."""
    guide = guide or {}
    parts = []
    if "farm_gate" in guide:
        parts.append(f"খামারে ৳{guide['farm_gate']['price_bdt_per_kg']:g}")
    wp = guide.get("wholesale_pattern") or {}
    if wp.get("this_month_avg_bdt_per_kg"):
        parts.append(f"পাইকারি ৳{wp['this_month_avg_bdt_per_kg']:g}")
    return ("দাম: " + ", ".join(parts) + "/কেজি") if parts else ""


def produce(state: dict, text: str | None, ctx) -> tuple[Screen, dict, dict | None]:
    from .produce import price_guide

    step, inp = state.get("step"), _d(text)
    if text is None:
        if not _district(ctx):
            return NO_DISTRICT, {"at": "main"}, None
        return paged(CROP_TITLE, _crop_labels(), 0), {"at": "produce", "sub": "produce", "step": "crop"}, None

    if step == "crop":
        kind, val, screen, state = _menu_step(CROP_TITLE, _crop_labels(), state, "cpage", inp)
        if kind == "back":
            return _home(ctx)
        if screen:
            return screen, state, None
        return Screen("কত কেজি?\nসংখ্যা লিখুন"), {**state, "step": "qty", "crop": CROP_CHOICES[val]}, None

    if step == "qty":
        try:
            qty = float(inp)
        except ValueError:
            qty = 0
        if not 0 < qty <= 1_000_000:
            return Screen("ভুল সংখ্যা! কত কেজি?"), state, None
        guide = guide_short(price_guide(state["crop"]))
        return (Screen("\n".join(filter(None, [guide, "আপনার দাম, টাকা/কেজি?", "* = ক্রেতা বলবে"]))),
                {**state, "step": "price", "qty": qty}, None)

    if step == "price":
        price = None
        if inp != "*":
            try:
                price = float(inp)
            except ValueError:
                price = -1
            if price <= 0:
                return Screen("ভুল দাম! টাকা/কেজি লিখুন\n* = ক্রেতা বলবে"), state, None
        ask = f", ৳{price:g}/কেজি" if price else ", দাম ক্রেতা বলবে"
        return (Screen(clip(f"{CROP_BN[state['crop']]} {state['qty']:g} কেজি{ask}", "1. তালিকা করুন\n2. বাতিল")),
                {**state, "step": "confirm", "price": price}, None)

    if step == "confirm":
        if inp == "1":
            action = {"kind": "market", "op": "list", "crop": state["crop"], "qty_kg": state["qty"],
                      "price": state.get("price")}
            return Screen("তালিকা হয়েছে। ক্রেতার অফার SMS-এ আসবে।", end=True), {"at": "main"}, action
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
