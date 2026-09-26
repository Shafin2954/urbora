"""SMS keyword commands for the marketplaces.

Checked before the agent sees an SMS (backend/channels/flows.py). Returns the
reply text when the message is a command, or None to let the agent answer.
Bangla and Western digits both work.

Farmers:
  বিক্রি আলু 500 কেজি 22 টাকা [রাজশাহী]   list a harvest (price and district optional)
  গ্রহণ 7 / বাতিল 7                          accept / reject offer #7
Dealers (recognised by the number they registered):
  হ্যাঁ 12 / না 12                            confirm / cancel order #12
  প্রস্তুত 12 / দেওয়া 12                      order ready / delivered
"""

from __future__ import annotations

import re

from backend.tools.ask import DISTRICT_BN

from . import db

_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
CROP_WORDS = {
    "বোরো": "boro_rice", "আমন": "aman_rice", "আলু": "potato", "সরিষা": "mustard", "মসুর": "lentil",
    "boro": "boro_rice", "aman": "aman_rice", "potato": "potato", "mustard": "mustard", "lentil": "lentil",
}
_DISTRICT_BY_BN = {bn: en for en, bn in DISTRICT_BN.items()}

_SELL = re.compile(r"^(?:বিক্রি|sell)\s+(\S+)\s+(\d+(?:\.\d+)?)\s*(?:কেজি|kg)?"
                   r"(?:\s+(\d+(?:\.\d+)?)\s*(?:টাকা|tk|taka))?(?:\s+(\S+))?\s*$", re.IGNORECASE)
_OFFER = re.compile(r"^(গ্রহণ|বাতিল|accept|reject)\s+#?(\d+)\s*$", re.IGNORECASE)
_DEALER = re.compile(r"^(হ্যাঁ|হ্যা|না|প্রস্তুত|দেওয়া|yes|no|ready|delivered)\s+#?(\d+)\s*$", re.IGNORECASE)
_DEALER_STATUS = {"হ্যাঁ": "confirmed", "হ্যা": "confirmed", "yes": "confirmed", "না": "cancelled",
                  "no": "cancelled", "প্রস্তুত": "ready", "ready": "ready", "দেওয়া": "delivered",
                  "delivered": "delivered"}


def try_handle(local_msisdn: str, text: str) -> str | None:
    msg = (text or "").strip().translate(_BN_DIGITS)
    if not msg:
        return None

    m = _DEALER.match(msg)
    if m:
        dealer = db.row("SELECT * FROM dealers WHERE msisdn = ?", (local_msisdn,))
        if dealer:
            from .inputs import MarketError, set_order_status
            status = _DEALER_STATUS[m.group(1).lower()]
            try:
                order = set_order_status(int(m.group(2)), status, dealer_id=dealer["dealer_id"])
            except MarketError as exc:
                return f"অর্ডার #{m.group(2)}: করা যায়নি ({exc})"
            return f"অর্ডার #{order['order_id']}: {order['status_bn']}। কৃষককে জানানো হয়েছে।"
        # Not a dealer: fall through — "না 3" from a farmer is ordinary chat.

    from backend.channels.identity import farm_id_for
    farm_id = farm_id_for(local_msisdn)

    m = _SELL.match(msg)
    if m:
        crop = CROP_WORDS.get(m.group(1).lower())
        if not crop:
            return "ফসলের নাম বুঝিনি। লিখুন যেমন: বিক্রি আলু 500 কেজি 22 টাকা"
        district = _DISTRICT_BY_BN.get(m.group(4) or "", m.group(4)) if m.group(4) else None
        from .produce import ProduceError, create_listing, guide_sms_line
        try:
            listing = create_listing(farm_id, crop, float(m.group(2)),
                                     float(m.group(3)) if m.group(3) else None, district, channel="sms")
        except ProduceError as exc:
            if "district" in str(exc):
                return "জেলার নাম সহ লিখুন, যেমন: বিক্রি আলু 500 কেজি 22 টাকা রাজশাহী"
            return f"তালিকা করা যায়নি: {exc}"
        guide = guide_sms_line(listing["price_guide"])
        return (f"তালিকা #{listing['listing_id']} হয়েছে। কাছের ক্রেতারা অফার পাঠাবেন।"
                + (f"\n{guide}" if guide else ""))

    m = _OFFER.match(msg)
    if m:
        from .produce import ProduceError, respond_to_offer
        accept = m.group(1).lower() in ("গ্রহণ", "accept")
        try:
            offer = respond_to_offer(farm_id, int(m.group(2)), accept)
        except ProduceError as exc:
            return f"অফার #{m.group(2)}: করা যায়নি ({exc})"
        if accept:
            return f"অফার #{offer['offer_id']} গৃহীত। ক্রেতার ফোন নম্বর আলাদা SMS-এ পাঠানো হয়েছে।"
        return f"অফার #{offer['offer_id']} বাতিল করা হয়েছে।"

    return None
